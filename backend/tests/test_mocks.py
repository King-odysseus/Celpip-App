"""Full mock orchestration, embargo, timing, and result-release tests."""
from datetime import timedelta
from uuid import uuid4

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.utils import timezone

from apps.accounts.models import User
from apps.assessments.models import AssessmentSession, SessionMode, SessionState
from apps.assessments.services import submit_session, submit_writing
from apps.assessments.storage import private_recording_storage
from apps.content.models import PublicationStatus, Skill
from apps.content.services import retire
from apps.mocks.models import MockAttempt, MockState, MockTaskState
from apps.mocks.services import (
    COMPONENT_ORDER,
    COMPONENT_TIMINGS,
    FORMAT_CODE,
    OFFICIAL_COUNTS,
    InvalidTransition,
    ResultsEmbargoed,
    advance_attempt,
    attempt_payload,
    create_attempt,
    ensure_format,
    refresh_attempt,
    results_payload,
    start_attempt,
)

pytestmark = pytest.mark.django_db

MOCKS_URL = "/api/v1/mocks/"
SESSIONS_URL = "/api/v1/sessions/"


@pytest.fixture
def mock_bank():
    call_command("seed_reading_content", verbosity=0)
    call_command("seed_writing_content", verbosity=0)
    call_command("seed_speaking_content", verbosity=0)
    call_command("seed_listening_content", verbosity=0)


@pytest.fixture
def user():
    return User.objects.create_user(identifier="mock-taker", password="secret1")


@pytest.fixture
def attempt(mock_bank, user):
    return create_attempt(user)


@pytest.fixture(autouse=True)
def isolated_recording_storage(tmp_path, monkeypatch):
    monkeypatch.setattr(private_recording_storage, "_location", str(tmp_path))
    private_recording_storage.__dict__.pop("base_location", None)
    private_recording_storage.__dict__.pop("location", None)
    yield tmp_path


def _submit_current(attempt: MockAttempt, user) -> MockAttempt:
    """Submit the current task's session using its correct skill path."""
    task = attempt.tasks.select_related("session").get(order=attempt.current_order)
    if task.section in (Skill.LISTENING, Skill.READING):
        submit_session(task.session)
    elif task.section == Skill.WRITING:
        submit_writing(
            task.session,
            final_text="A complete mock response with enough words to be accepted.",
        )
    else:
        # Speaking recording upload is covered by test_speaking; the mock state
        # machine only requires the session to be submitted.
        AssessmentSession.objects.filter(pk=task.session_id).update(
            state=SessionState.SUBMITTED, submitted_at=timezone.now()
        )
    return advance_attempt(attempt.id, user, expected_order=attempt.current_order)[0]


def _advance_to(attempt: MockAttempt, user, section) -> MockAttempt:
    """Start the attempt and submit objective tasks until ``section`` is current."""
    attempt, _ = start_attempt(attempt.id, user)
    while attempt.current_section != section:
        attempt = _submit_current(attempt, user)
    return attempt


def _recording():
    return SimpleUploadedFile(
        "response.webm", b"\x1aE\xdf\xa3" + b"practice-audio" * 20, content_type="audio/webm"
    )


# --- Assembly and format-version ------------------------------------------


def test_exact_format_assembly_follows_official_constants(attempt):
    tasks = list(attempt.tasks.select_related("session", "content_version"))
    assert len(tasks) == 20
    assert [task.section for task in tasks[:6]] == [Skill.LISTENING] * 6
    assert [task.section for task in tasks[6:10]] == [Skill.READING] * 4
    assert [task.section for task in tasks[10:12]] == [Skill.WRITING] * 2
    assert [task.section for task in tasks[12:]] == [Skill.SPEAKING] * 8

    # Each official task family appears exactly once, in component order.
    assert sorted(task.task_type for task in tasks) == sorted(OFFICIAL_COUNTS)
    assert all(task.session.mode == SessionMode.MOCK for task in tasks)
    assert all(task.session.state == SessionState.ACTIVE for task in tasks)

    snapshot = attempt.format_snapshot
    assert snapshot["code"] == FORMAT_CODE
    assert snapshot["component_order"] == COMPONENT_ORDER
    assert snapshot["component_timings"] == COMPONENT_TIMINGS
    assert snapshot["scope"] == "compact_task_family_mock"
    assert "limitation" in snapshot

    # Frozen per-task and per-session snapshots agree with the source content.
    first = tasks[0]
    assert first.snapshot["skill"] == Skill.LISTENING
    assert first.session.items.get().snapshot["title"] == first.snapshot["title"]


def test_ensure_format_is_idempotent_and_complete(mock_bank):
    version = ensure_format()
    again = ensure_format()

    assert version.pk == again.pk
    assert version.code == FORMAT_CODE
    assert version.component_order == COMPONENT_ORDER
    assert version.component_timings == COMPONENT_TIMINGS
    assert len(version.task_structure) == 20
    skills = [row["skill"] for row in version.task_structure]
    assert skills.index(Skill.LISTENING) < skills.index(Skill.READING)
    assert skills.index(Skill.READING) < skills.index(Skill.WRITING)
    assert skills.index(Skill.WRITING) < skills.index(Skill.SPEAKING)


# --- Start, progression, and state machine ---------------------------------


def test_start_is_idempotent_and_sets_section_deadline(attempt, user):
    started, replayed = start_attempt(attempt.id, user)

    assert replayed is False
    assert started.state == MockState.ACTIVE
    assert started.current_section == Skill.LISTENING
    assert started.current_order == 1
    assert started.section_deadline_at is not None
    assert started.started_at is not None

    first_task = started.tasks.get(order=1)
    assert first_task.state == MockTaskState.CURRENT
    assert first_task.session.deadline_at is not None

    # A second start replays without re-timing the section.
    replay, replayed = start_attempt(attempt.id, user)
    assert replayed is True
    assert replay.section_deadline_at == started.section_deadline_at


def test_section_deadline_persists_across_refresh_and_within_section(attempt, user):
    started, _ = start_attempt(attempt.id, user)
    first_deadline = started.section_deadline_at

    # Every Listening session shares the section deadline from the moment the
    # section begins, and a refresh does not re-time or clear it.
    listening_tasks = started.tasks.filter(section=Skill.LISTENING)
    assert all(task.session.deadline_at == first_deadline for task in listening_tasks)

    refreshed = refresh_attempt(attempt.id, user)
    assert refreshed.section_deadline_at == first_deadline
    assert refreshed.tasks.get(order=2).session.deadline_at == first_deadline

    # Advancing within the section keeps the same deadline for the next task.
    _submit_current(refreshed, user)
    after = refresh_attempt(attempt.id, user)
    assert after.current_order == 2
    assert after.section_deadline_at == first_deadline
    assert after.tasks.get(order=2).session.deadline_at == first_deadline


def test_advance_requires_submitted_current_task(attempt, user):
    start_attempt(attempt.id, user)
    with pytest.raises(InvalidTransition, match="Submit the current task"):
        advance_attempt(attempt.id, user, expected_order=1)


def test_advance_progresses_within_section(attempt, user):
    attempt, _ = start_attempt(attempt.id, user)
    _submit_current(attempt, user)

    refreshed = refresh_attempt(attempt.id, user)
    assert refreshed.current_order == 2
    assert refreshed.current_section == Skill.LISTENING
    assert refreshed.tasks.get(order=1).state == MockTaskState.SUBMITTED
    assert refreshed.tasks.get(order=2).state == MockTaskState.CURRENT


def test_objective_submit_and_stale_advance_are_idempotent(attempt, user):
    start_attempt(attempt.id, user)
    task = attempt.tasks.get(order=1)

    first = submit_session(task.session)
    replay = submit_session(task.session)
    assert replay.pk == first.pk
    assert first.raw_possible == 3

    advance_attempt(attempt.id, user, expected_order=1)
    _, replayed = advance_attempt(attempt.id, user, expected_order=1)
    assert replayed is True


def test_section_timeout_skips_remaining_and_advances(attempt, user):
    start_attempt(attempt.id, user)
    MockAttempt.objects.filter(pk=attempt.id).update(
        section_deadline_at=timezone.now() - timedelta(seconds=1)
    )

    refreshed = refresh_attempt(attempt.id, user)

    assert refreshed.state == MockState.ACTIVE
    assert refreshed.current_section == Skill.READING
    assert refreshed.current_order == 7
    skipped = refreshed.tasks.filter(section=Skill.LISTENING, state=MockTaskState.SKIPPED)
    assert skipped.count() == 6
    for task in refreshed.tasks.filter(section=Skill.LISTENING):
        assert task.session.state == SessionState.SUBMITTED
    assert refreshed.tasks.get(order=7).state == MockTaskState.CURRENT


def test_expiry_keeps_submitted_current_and_skips_only_remainder(attempt, user):
    start_attempt(attempt.id, user)
    submit_session(attempt.tasks.get(order=1).session)
    MockAttempt.objects.filter(pk=attempt.id).update(
        section_deadline_at=timezone.now() - timedelta(seconds=1)
    )

    refreshed, replayed = advance_attempt(attempt.id, user, expected_order=1)

    assert replayed is False
    assert refreshed.state == MockState.ACTIVE
    assert refreshed.current_section == Skill.READING
    assert refreshed.current_order == 7
    assert refreshed.tasks.get(order=1).state == MockTaskState.SUBMITTED
    assert refreshed.tasks.get(order=1).session.state == SessionState.SUBMITTED
    skipped = refreshed.tasks.filter(section=Skill.LISTENING, state=MockTaskState.SKIPPED)
    assert skipped.count() == 5
    for task in refreshed.tasks.filter(section=Skill.LISTENING, order__gte=2):
        assert task.session.state == SessionState.SUBMITTED
    assert refreshed.tasks.get(order=7).state == MockTaskState.CURRENT


def test_full_mock_completes_and_releases_results(attempt, user):
    attempt, _ = start_attempt(attempt.id, user)
    for _ in range(20):
        attempt = _submit_current(attempt, user)

    attempt.refresh_from_db()
    assert attempt.state == MockState.COMPLETED
    assert attempt.completed_at is not None

    payload = results_payload(attempt)
    assert payload["attempt_id"] == str(attempt.id)
    assert payload["overall_score"] is None
    components = {item["skill"]: item for item in payload["components"]}
    assert list(components) == COMPONENT_ORDER

    assert components[Skill.LISTENING]["measure"] == "practice_accuracy"
    assert components[Skill.LISTENING]["raw_possible"] == 18
    assert components[Skill.READING]["raw_possible"] == 12
    assert components[Skill.WRITING]["measure"] == "ai_assisted_practice_estimate"
    assert components[Skill.WRITING]["tasks_total"] == 2
    assert components[Skill.SPEAKING]["tasks_total"] == 8


# --- Results embargo -------------------------------------------------------


def test_results_are_embargoed_until_attempt_completes(attempt):
    with pytest.raises(ResultsEmbargoed, match="only after all four components"):
        results_payload(attempt)


def test_session_submit_withholds_corrections_until_complete(api_client, attempt, user):
    start_attempt(attempt.id, user)
    session = attempt.tasks.get(order=1).session
    api_client.force_authenticate(user)

    submitted = api_client.post(f"{SESSIONS_URL}{session.id}/submit/")
    assert submitted.status_code == 200
    payload = submitted.json()
    assert payload["awaiting_mock_results"] is True
    assert payload["mock"]["attempt_id"] == str(attempt.id)
    assert "outcomes" not in payload
    assert "raw_correct" not in payload

    results = api_client.get(f"{SESSIONS_URL}{session.id}/results/")
    assert results.status_code == 409
    assert results.json()["code"] == "mock_results_embargoed"


def test_session_results_release_after_completion(api_client, attempt, user):
    start_attempt(attempt.id, user)
    session = attempt.tasks.get(order=1).session
    submit_session(session)
    MockAttempt.objects.filter(pk=attempt.id).update(
        state=MockState.COMPLETED, completed_at=timezone.now()
    )
    api_client.force_authenticate(user)

    results = api_client.get(f"{SESSIONS_URL}{session.id}/results/")
    assert results.status_code == 200
    assert "outcomes" in results.json()
    assert results.json()["raw_possible"] == 3


def test_mock_results_endpoint_is_embargoed(api_client, attempt, user):
    start_attempt(attempt.id, user)
    api_client.force_authenticate(user)

    response = api_client.get(f"{MOCKS_URL}{attempt.id}/results/")
    assert response.status_code == 409
    assert response.json()["code"] == "mock_results_embargoed"


def test_mock_writing_submit_and_detail_hide_review_and_ai(api_client, attempt, user):
    attempt = _advance_to(attempt, user, Skill.WRITING)
    session = attempt.tasks.get(order=attempt.current_order).session
    api_client.force_authenticate(user)

    submitted = api_client.post(
        f"{SESSIONS_URL}{session.id}/writing/submit/",
        {"text": "A complete mock writing response with enough words to be accepted."},
        format="json",
    )
    assert submitted.status_code == 200
    body = submitted.json()
    assert body["awaiting_mock_results"] is True
    assert "review" not in body
    assert "estimated_level" not in body
    assert "transcript" not in body

    detail = api_client.get(f"{SESSIONS_URL}{session.id}/writing/")
    assert detail.status_code == 200
    body = detail.json()
    assert "review" not in body
    assert "estimated_level" not in body
    assert "transcript" not in body

    feedback = api_client.get(f"{SESSIONS_URL}{session.id}/ai-feedback/")
    assert feedback.status_code == 409
    assert feedback.json()["code"] == "mock_results_embargoed"


def test_mock_speaking_submit_and_detail_hide_review_and_ai(api_client, attempt, user):
    attempt = _advance_to(attempt, user, Skill.SPEAKING)
    session = attempt.tasks.get(order=attempt.current_order).session
    api_client.force_authenticate(user)

    saved = api_client.put(
        f"{SESSIONS_URL}{session.id}/speaking/",
        {
            "audio": _recording(),
            "duration_ms": 45_000,
            "expected_revision": 0,
        },
        format="multipart",
        HTTP_IDEMPOTENCY_KEY=str(uuid4()),
    )
    assert saved.status_code == 200

    submitted = api_client.post(f"{SESSIONS_URL}{session.id}/speaking/submit/")
    assert submitted.status_code == 200
    body = submitted.json()
    assert body["awaiting_mock_results"] is True
    assert "review" not in body
    assert "estimated_level" not in body
    assert "transcript" not in body

    detail = api_client.get(f"{SESSIONS_URL}{session.id}/speaking/")
    assert detail.status_code == 200
    body = detail.json()
    assert "review" not in body
    assert "estimated_level" not in body
    assert "transcript" not in body

    feedback = api_client.get(f"{SESSIONS_URL}{session.id}/ai-feedback/")
    assert feedback.status_code == 409
    assert feedback.json()["code"] == "mock_results_embargoed"


# --- HTTP surface and ownership --------------------------------------------


def test_list_create_and_ownership(api_client, mock_bank, user):
    api_client.force_authenticate(user)
    created = api_client.post(f"{MOCKS_URL}")
    assert created.status_code == 201
    attempt_id = created.json()["id"]

    listed = api_client.get(f"{MOCKS_URL}")
    assert listed.status_code == 200
    assert listed.json()["count"] == 1
    assert listed.json()["results"][0]["id"] == attempt_id

    detail = api_client.get(f"{MOCKS_URL}{attempt_id}/")
    assert detail.status_code == 200
    assert len(detail.json()["tasks"]) == 20

    stranger = User.objects.create_user(identifier="mock-stranger", password="secret1")
    api_client.force_authenticate(stranger)
    assert api_client.get(f"{MOCKS_URL}{attempt_id}/").status_code == 404
    assert api_client.post(f"{MOCKS_URL}{attempt_id}/start/").status_code == 404


def test_public_session_start_rejects_mock_mode(api_client, mock_bank):
    response = api_client.post(
        f"{SESSIONS_URL}",
        {"content_slug": "garden-plot-renewal", "mode": "mock"},
        format="json",
    )
    assert response.status_code == 400
    assert "mock" in str(response.json())


# --- Frozen content integrity ----------------------------------------------


def test_mock_task_frozen_fields_are_immutable(attempt):
    task = attempt.tasks.get(order=1)
    task.order = 99
    with pytest.raises(ValidationError, match="immutable"):
        task.save()


def test_retired_content_does_not_break_frozen_attempt(attempt):
    task = attempt.tasks.get(order=1)
    version = task.content_version
    frozen_title = task.session.items.get().snapshot["title"]

    retired = retire(version)
    assert retired.status == PublicationStatus.RETIRED

    task.refresh_from_db()
    assert task.snapshot["title"] == frozen_title
    assert task.session.items.get().snapshot["title"] == frozen_title


def test_attempt_payload_reports_progress_and_current_task(attempt, user):
    attempt, _ = start_attempt(attempt.id, user)
    payload = attempt_payload(attempt)

    assert payload["state"] == MockState.ACTIVE
    assert payload["current_task"]["order"] == 1
    assert payload["current_task"]["kind"] == "objective"
    assert payload["progress"] == {"completed": 0, "total": 20}
    assert payload["disclaimer"]
    assert len(payload["tasks"]) == 20
