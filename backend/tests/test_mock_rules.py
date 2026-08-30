"""Mock exam-mode rules: explicit timing/submission/replay contract and deadline cut-off."""
from datetime import timedelta

import pytest
from django.core.management import call_command
from django.utils import timezone

from apps.accounts.models import User
from apps.assessments.models import AssessmentSession, SessionState
from apps.assessments.services import submit_session, submit_writing
from apps.content.models import Skill
from apps.mocks.models import MockAttempt, MockState
from apps.mocks.services import (
    advance_attempt,
    attempt_payload,
    create_attempt,
    start_attempt,
)

pytestmark = pytest.mark.django_db

SESSIONS_URL = "/api/v1/sessions/"


@pytest.fixture
def mock_bank():
    for command in (
        "seed_reading_content",
        "seed_writing_content",
        "seed_speaking_content",
        "seed_listening_content",
    ):
        call_command(command, verbosity=0)


@pytest.fixture
def user():
    return User.objects.create_user(identifier="mock-rules", password="secret1")


@pytest.fixture
def attempt(mock_bank, user):
    return create_attempt(user)


def _submit_current(attempt: MockAttempt, user) -> MockAttempt:
    task = attempt.tasks.select_related("session").get(order=attempt.current_order)
    if task.section in (Skill.LISTENING, Skill.READING):
        submit_session(task.session)
    elif task.section == Skill.WRITING:
        submit_writing(
            task.session,
            final_text="A complete mock response with enough words to be accepted.",
        )
    else:
        AssessmentSession.objects.filter(pk=task.session_id).update(
            state=SessionState.SUBMITTED, submitted_at=timezone.now()
        )
    return advance_attempt(attempt.id, user, expected_order=attempt.current_order)[0]


def _advance_to(attempt: MockAttempt, user, section: str) -> MockAttempt:
    attempt, _ = start_attempt(attempt.id, user)
    while attempt.current_section != section:
        attempt = _submit_current(attempt, user)
    return attempt


def _expire_session(attempt: MockAttempt, order: int) -> AssessmentSession:
    session = attempt.tasks.select_related("session").get(order=order).session
    AssessmentSession.objects.filter(pk=session.id).update(
        deadline_at=timezone.now() - timedelta(seconds=1)
    )
    session.refresh_from_db()
    assert session.state == SessionState.ACTIVE
    return session


# --- Rules contract -------------------------------------------------------


def test_attempt_payload_exposes_explicit_rules(attempt, user):
    attempt, _ = start_attempt(attempt.id, user)
    rules = attempt_payload(attempt)["rules"]

    timing = rules["timing"]
    assert timing["running"] is True
    assert timing["auto_submits_on_expiry"] is True
    assert timing["section"] == Skill.LISTENING
    assert timing["per_section_seconds"] == 3300
    assert timing["section_deadline_at"] == attempt.section_deadline_at
    assert timing["remaining_seconds"] is not None
    assert timing["remaining_seconds"] > 0
    assert timing["expired"] is False

    assert rules["submission"] == {
        "editable_after_submit": False,
        "results_embargoed_until_complete": True,
    }
    assert rules["replay"] == {
        "objective_answers_replayable": False,
        "speaking_retry_allowed": False,
        "audio_playback": "one_play",
    }


def test_rules_report_no_running_clock_before_start(attempt):
    rules = attempt_payload(attempt)["rules"]
    assert rules["timing"]["running"] is False
    assert rules["timing"]["auto_submits_on_expiry"] is True
    assert "remaining_seconds" not in rules["timing"]


# --- Deadline cut-off (mock only; practice keeps late submit) -------------


def test_mock_objective_submit_blocked_after_deadline(api_client, attempt, user):
    start_attempt(attempt.id, user)
    session = _expire_session(attempt, order=1)
    api_client.force_authenticate(user)

    response = api_client.post(f"{SESSIONS_URL}{session.id}/submit/")
    assert response.status_code == 409
    assert response.json()["code"] == "session_deadline_passed"
    session.refresh_from_db()
    assert session.state == SessionState.ACTIVE


def test_mock_writing_submit_blocked_after_deadline(api_client, attempt, user):
    attempt = _advance_to(attempt, user, Skill.WRITING)
    session = _expire_session(attempt, order=attempt.current_order)
    api_client.force_authenticate(user)

    response = api_client.post(
        f"{SESSIONS_URL}{session.id}/writing/submit/",
        {"text": "A complete mock writing response with enough words to be accepted."},
        format="json",
    )
    assert response.status_code == 409
    assert response.json()["code"] == "session_deadline_passed"


def test_mock_speaking_submit_blocked_after_deadline(api_client, attempt, user):
    attempt = _advance_to(attempt, user, Skill.SPEAKING)
    session = _expire_session(attempt, order=attempt.current_order)
    api_client.force_authenticate(user)

    response = api_client.post(f"{SESSIONS_URL}{session.id}/speaking/submit/")
    assert response.status_code == 409
    assert response.json()["code"] == "session_deadline_passed"


def test_practice_late_submit_still_allowed(api_client, user):
    call_command("seed_reading_content", verbosity=0)
    api_client.force_authenticate(user)
    started = api_client.post(
        SESSIONS_URL,
        {
            "content_slug": "garden-plot-renewal",
            "mode": "practice",
            "time_limit_seconds": 60,
        },
        format="json",
    )
    assert started.status_code == 201
    session_id = started.json()["id"]
    AssessmentSession.objects.filter(pk=session_id).update(
        deadline_at=timezone.now() - timedelta(seconds=1)
    )

    response = api_client.post(f"{SESSIONS_URL}{session_id}/submit/")
    assert response.status_code == 200
    assert response.json()["raw_possible"] == 4
