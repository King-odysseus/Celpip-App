"""Writing seeds/catalog, validation, and constructed-response session tests."""
from datetime import timedelta
from io import StringIO
from uuid import uuid4

import pytest
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.utils import timezone

from apps.accounts.models import User
from apps.assessments.models import AssessmentSession, WritingSubmission
from apps.content.models import (
    ContentItem,
    ContentVersion,
    Question,
    Skill,
    TaskType,
)
from apps.content.services import validate_content_version

pytestmark = pytest.mark.django_db

SESSIONS_URL = "/api/v1/sessions/"
EMAIL_SLUG = "email-noisy-renovation"
SURVEY_SLUG = "survey-library-weekend-hours"


@pytest.fixture
def seeded_writing():
    call_command("seed_writing_content", verbosity=0)
    return EMAIL_SLUG


def start(api_client, slug=EMAIL_SLUG, mode="practice", **extra):
    payload = {"content_slug": slug, "mode": mode} | extra
    return api_client.post(SESSIONS_URL, payload, format="json")


def guest_headers(started):
    return {"HTTP_X_GUEST_TOKEN": started.json()["guest_token"]}


def writing_url(started):
    return f"{SESSIONS_URL}{started.json()['id']}/writing/"


def submit_url(started):
    return f"{SESSIONS_URL}{started.json()['id']}/writing/submit/"


def put_writing(api_client, started, text, expected_revision, key=None, **headers):
    return api_client.put(
        writing_url(started),
        {"text": text, "expected_revision": expected_revision},
        format="json",
        HTTP_IDEMPOTENCY_KEY=key or str(uuid4()),
        **guest_headers(started),
        **headers,
    )


# --- Seeds & catalog -------------------------------------------------------


def test_seed_is_idempotent_with_reviewed_original_prompts():
    first, second = StringIO(), StringIO()
    call_command("seed_writing_content", stdout=first)
    call_command("seed_writing_content", stdout=second)

    assert "created 152" in first.getvalue()
    assert "created 0" in second.getvalue()
    assert TaskType.objects.filter(skill=Skill.WRITING).count() == 2
    assert ContentItem.objects.filter(task_type__skill=Skill.WRITING).count() == 152
    assert (
        ContentVersion.objects.filter(
            item__task_type__skill=Skill.WRITING, status="published"
        ).count()
        == 152
    )
    # Writing prompts carry no objective questions.
    assert Question.objects.filter(
        content_version__item__task_type__skill=Skill.WRITING
    ).count() == 0
    assert not ContentVersion.objects.filter(
        item__task_type__skill=Skill.WRITING, reviewer_id=None
    ).exists()


def test_public_writing_catalog_and_detail(api_client, seeded_writing):
    catalog = api_client.get("/api/v1/content/writing/")
    assert catalog.status_code == 200
    assert catalog.json()["count"] == 152

    filtered = api_client.get(
        "/api/v1/content/writing/", {"task_type": "writing_survey"}
    )
    assert filtered.json()["count"] == 76

    detail = api_client.get(f"/api/v1/content/writing/{SURVEY_SLUG}/")
    assert detail.status_code == 200
    payload = detail.json()
    assert payload["questions"] == []
    stimulus = payload["stimulus"]
    assert stimulus["task_kind"] == "survey"
    assert len(stimulus["options"]) == 2
    assert stimulus["target_words"] == {"min": 150, "max": 200}
    assert stimulus["suggested_duration_seconds"] == 26 * 60


# --- Skill-aware validation ------------------------------------------------


def _writing_version(stimulus, *, kind="writing_email"):
    task_type = TaskType.objects.create(
        code=f"{kind}-test",
        skill=Skill.WRITING,
        title="Writing test task",
        part_number=1,
        description="A writing task.",
    )
    item = ContentItem.objects.create(
        slug="writing-validation-fixture",
        task_type=task_type,
        title="Writing validation fixture",
        topic="Testing",
        difficulty=1,
        estimated_level=6,
        provenance="Original fixture authored for automated tests.",
    )
    return ContentVersion.objects.create(
        item=item,
        version=1,
        instructions="Write an email.",
        stimulus=stimulus,
    )


def test_valid_writing_prompt_needs_no_questions():
    version = _writing_version(
        {
            "type": "writing_prompt",
            "task_kind": "email",
            "scenario": "Write to your manager about noise.",
            "requested_points": ["Explain the problem."],
            "target_words": {"min": 150, "max": 200},
            "suggested_duration_seconds": 1620,
        }
    )
    assert validate_content_version(version) == []


def test_invalid_writing_prompt_is_rejected():
    version = _writing_version(
        {
            "type": "not_a_writing_prompt",
            "task_kind": "survey",
            "scenario": "",
            "requested_points": [],
            "target_words": {"min": 0, "max": 0},
            "suggested_duration_seconds": 0,
            "options": [{"key": "a", "label": "Only one"}],
        }
    )
    codes = {issue.code for issue in validate_content_version(version)}
    assert "invalid_writing_stimulus_type" in codes
    assert "missing_writing_scenario" in codes
    assert "missing_writing_points" in codes
    assert "invalid_target_words" in codes
    assert "missing_writing_duration" in codes
    assert "missing_survey_options" in codes
    assert "missing_survey_question" in codes


def test_reading_still_requires_questions():
    task_type = TaskType.objects.create(
        code="reading-needs-questions",
        skill=Skill.READING,
        title="Reading task",
        part_number=1,
        description="Reading task.",
    )
    item = ContentItem.objects.create(
        slug="reading-no-questions",
        task_type=task_type,
        title="Reading without questions",
        topic="Testing",
        difficulty=1,
        estimated_level=5,
        provenance="Original fixture.",
    )
    version = ContentVersion.objects.create(
        item=item,
        version=1,
        instructions="Read.",
        stimulus={"type": "article", "body": "A passage."},
    )
    codes = {issue.code for issue in validate_content_version(version)}
    assert "missing_questions" in codes


def test_validate_content_command_accepts_writing_bank():
    call_command("seed_writing_content", verbosity=0)
    output = StringIO()
    call_command("validate_content", stdout=output)
    assert "content version" in output.getvalue()


# --- Session lifecycle & frozen content ------------------------------------


def test_writing_session_freezes_prompt_snapshot(api_client, seeded_writing):
    started = start(api_client)
    session = AssessmentSession.objects.get(pk=started.json()["id"])
    snapshot = session.items.get().snapshot
    assert snapshot["skill"] == "writing"
    assert snapshot["questions"] == []
    assert snapshot["stimulus"]["task_kind"] == "email"

    detail = api_client.get(writing_url(started), **guest_headers(started))
    assert detail.status_code == 200
    body = detail.json()
    assert body["content"]["stimulus"]["scenario"]
    assert "guidance" not in body["content"]["stimulus"]
    assert [d["label"] for d in body["rubric"]["dimensions"]] == [
        "Content/Coherence",
        "Vocabulary",
        "Readability",
        "Task Fulfillment",
    ]
    assert body["submission"] is None

    learned = start(api_client, mode="learn")
    learn_detail = api_client.get(writing_url(learned), **guest_headers(learned))
    assert "guidance" in learn_detail.json()["content"]["stimulus"]


def test_server_word_count_and_autosave_revision(api_client, seeded_writing):
    started = start(api_client)
    first = put_writing(api_client, started, "One two three four five.", 0)
    assert first.status_code == 200
    assert first.json()["word_count"] == 5
    assert first.json()["revision"] == 1

    second = put_writing(api_client, started, "Now there are six words here.", 1)
    assert second.status_code == 200
    assert second.json()["word_count"] == 6
    assert second.json()["revision"] == 2
    assert WritingSubmission.objects.get().text == "Now there are six words here."


def test_stale_revision_conflict(api_client, seeded_writing):
    started = start(api_client)
    put_writing(api_client, started, "First draft.", 0)
    stale = put_writing(api_client, started, "Second draft.", 0)
    assert stale.status_code == 409
    assert stale.json()["code"] == "stale_revision"


def test_idempotent_replay_and_conflict(api_client, seeded_writing):
    started = start(api_client)
    key = str(uuid4())
    first = put_writing(api_client, started, "Draft text here.", 0, key=key)
    replay = put_writing(api_client, started, "Draft text here.", 0, key=key)
    assert first.status_code == replay.status_code == 200
    assert replay.json()["replayed"] is True
    assert WritingSubmission.objects.get().revision == 1

    conflict = put_writing(api_client, started, "Different text.", 0, key=key)
    assert conflict.status_code == 409
    assert conflict.json()["code"] == "idempotency_conflict"


def test_length_limit_rejected(api_client, seeded_writing):
    started = start(api_client)
    too_long = put_writing(api_client, started, "word " * 3000, 0)
    assert too_long.status_code == 400
    assert too_long.json()["code"] == "response_too_long"


def test_guest_token_required_and_ownership_enforced(api_client, seeded_writing):
    owner = User.objects.create_user(identifier="owner", password="secret1")
    api_client.force_authenticate(owner)
    started = start(api_client)
    assert "guest_token" not in started.json()

    stranger = User.objects.create_user(identifier="stranger", password="secret1")
    api_client.force_authenticate(stranger)
    denied = api_client.get(writing_url(started))
    assert denied.status_code == 403
    assert denied.json()["code"] == "session_access_denied"


def test_guest_missing_token_is_forbidden(api_client, seeded_writing):
    started = start(api_client)
    no_token = api_client.get(writing_url(started))
    assert no_token.status_code == 403


def test_deadline_blocks_writing_save(api_client, seeded_writing):
    started = start(api_client, time_limit_seconds=60)
    AssessmentSession.objects.filter(pk=started.json()["id"]).update(
        deadline_at=timezone.now() - timedelta(seconds=1)
    )
    blocked = put_writing(api_client, started, "Too late.", 0)
    assert blocked.status_code == 409
    assert blocked.json()["code"] == "session_deadline_passed"


def test_submit_atomically_freezes_latest_text_after_deadline(api_client, seeded_writing):
    started = start(api_client, time_limit_seconds=60)
    put_writing(api_client, started, "An older autosaved draft.", 0)
    AssessmentSession.objects.filter(pk=started.json()["id"]).update(
        deadline_at=timezone.now() - timedelta(seconds=1)
    )

    latest = "The latest local draft survives the timer ending."
    submitted = api_client.post(
        submit_url(started),
        {"text": latest},
        format="json",
        **guest_headers(started),
    )

    assert submitted.status_code == 200
    assert submitted.json()["submission"]["text"] == latest
    assert WritingSubmission.objects.get().text == latest


def test_submit_freezes_response_and_returns_honest_review(api_client, seeded_writing):
    started = start(api_client)
    body = " ".join(["word"] * 160)
    put_writing(api_client, started, body, 0)

    submitted = api_client.post(submit_url(started), **guest_headers(started))
    assert submitted.status_code == 200
    payload = submitted.json()
    assert payload["state"] == "submitted"
    assert payload["word_count"] == 160
    assert payload["within_target"] is True
    assert payload["estimated_level"] is None
    assert "not an official CELPIP" in payload["disclaimer"]
    labels = [d["label"] for d in payload["rubric"]["dimensions"]]
    assert "Task Fulfillment" in labels

    session = AssessmentSession.objects.get(pk=started.json()["id"])
    assert session.state == "submitted"
    assert WritingSubmission.objects.get().submitted_at is not None


def test_cannot_edit_after_submit(api_client, seeded_writing):
    started = start(api_client)
    put_writing(api_client, started, "A complete response.", 0)
    api_client.post(submit_url(started), **guest_headers(started))

    blocked = put_writing(api_client, started, "Trying to change it.", 1)
    assert blocked.status_code == 409
    assert blocked.json()["code"] == "session_not_active"
    assert WritingSubmission.objects.get().text == "A complete response."


def test_submitted_response_is_immutable_at_model_boundary(api_client, seeded_writing):
    started = start(api_client)
    put_writing(api_client, started, "A complete response.", 0)
    api_client.post(submit_url(started), **guest_headers(started))

    submission = WritingSubmission.objects.get()
    submission.text = "Changed outside the service layer."
    with pytest.raises(ValidationError, match="immutable"):
        submission.save()
    with pytest.raises(ValidationError, match="immutable"):
        submission.delete()


def test_repeat_submit_is_idempotent(api_client, seeded_writing):
    started = start(api_client)
    put_writing(api_client, started, "A complete response here.", 0)
    first = api_client.post(submit_url(started), **guest_headers(started))
    replay = api_client.post(submit_url(started), **guest_headers(started))
    assert first.status_code == replay.status_code == 200
    assert first.json()["replayed"] is False
    assert replay.json()["replayed"] is True


def test_blank_submit_is_rejected(api_client, seeded_writing):
    started = start(api_client)
    put_writing(api_client, started, "   ", 0)
    empty = api_client.post(submit_url(started), **guest_headers(started))
    assert empty.status_code == 400
    assert empty.json()["code"] == "empty_response"


def test_objective_submit_rejects_writing_session(api_client, seeded_writing):
    started = start(api_client)
    wrong = api_client.post(
        f"{SESSIONS_URL}{started.json()['id']}/submit/", **guest_headers(started)
    )
    assert wrong.status_code == 400
    assert wrong.json()["code"] == "wrong_skill"


def test_published_writing_content_is_immutable(seeded_writing):
    version = ContentVersion.objects.filter(
        item__slug=EMAIL_SLUG, status="published"
    ).get()
    version.instructions = "Changed"
    with pytest.raises(ValidationError, match="immutable"):
        version.save()
