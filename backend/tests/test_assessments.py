"""Assessment ownership, timing, autosave, release, and scoring tests."""
from datetime import timedelta
from uuid import uuid4

import pytest
from django.core.management import call_command
from django.utils import timezone

from apps.accounts.models import User
from apps.assessments.models import AssessmentSession, Response

pytestmark = pytest.mark.django_db

SESSIONS_URL = "/api/v1/sessions/"


@pytest.fixture
def seeded_content():
    call_command("seed_reading_content", verbosity=0)
    return "garden-plot-renewal"


def start(api_client, slug, mode="practice", **extra):
    payload = {"content_slug": slug, "mode": mode} | extra
    return api_client.post(SESSIONS_URL, payload, format="json")


def guest_headers(started):
    return {"HTTP_X_GUEST_TOKEN": started.json()["guest_token"]}


def save_url(started, question_id):
    return f"/api/v1/sessions/{started.json()['id']}/responses/{question_id}/"


def test_guest_start_returns_one_time_token_and_safe_frozen_content(api_client, seeded_content):
    response = start(api_client, seeded_content)

    assert response.status_code == 201
    payload = response.json()
    session = AssessmentSession.objects.get(pk=payload["id"])
    assert payload["guest_token"]
    assert session.guest_token_hash
    assert payload["guest_token"] != session.guest_token_hash
    assert session.guest_expires_at > timezone.now()
    assert payload["deadline_at"] is not None
    assert "is_correct" not in str(payload["content"])
    assert "explanation" not in str(payload["content"])
    assert "evidence" not in str(payload["content"])
    assert session.items.get().snapshot["questions"][0]["choices"][0]["is_correct"] in {
        True,
        False,
    }


def test_learn_session_has_no_deadline_and_includes_learning_notes(api_client, seeded_content):
    response = start(api_client, seeded_content, mode="learn")

    assert response.status_code == 201
    assert response.json()["deadline_at"] is None
    assert response.json()["content"]["learning_notes"]


def test_guest_token_is_required_and_expires(api_client, seeded_content):
    started = start(api_client, seeded_content)
    detail_url = f"{SESSIONS_URL}{started.json()['id']}/"

    assert api_client.get(detail_url).status_code == 403
    assert api_client.get(detail_url, **guest_headers(started)).status_code == 200

    AssessmentSession.objects.filter(pk=started.json()["id"]).update(
        guest_expires_at=timezone.now() - timedelta(seconds=1)
    )
    expired = api_client.get(detail_url, **guest_headers(started))
    assert expired.status_code == 403
    assert expired.json()["code"] == "guest_access_expired"


def test_authenticated_session_is_private(api_client, seeded_content):
    owner = User.objects.create_user(identifier="owner", password="secret1")
    stranger = User.objects.create_user(identifier="stranger", password="secret1")
    api_client.force_authenticate(owner)
    started = start(api_client, seeded_content)
    assert "guest_token" not in started.json()

    api_client.force_authenticate(stranger)
    detail = api_client.get(f"{SESSIONS_URL}{started.json()['id']}/")
    assert detail.status_code == 403
    assert detail.json()["code"] == "session_access_denied"


def test_learn_save_releases_immediate_feedback(api_client, seeded_content):
    started = start(api_client, seeded_content, mode="learn")
    question = started.json()["content"]["questions"][0]
    choice_id = question["choices"][0]["id"]

    response = api_client.put(
        save_url(started, question["id"]),
        {"selected_choice_id": choice_id, "expected_revision": 0},
        format="json",
        HTTP_IDEMPOTENCY_KEY=str(uuid4()),
        **guest_headers(started),
    )

    assert response.status_code == 200
    assert response.json()["revision"] == 1
    assert "feedback" in response.json()
    assert "correct_choice_id" in response.json()["feedback"]


def test_practice_hides_feedback_until_submit(api_client, seeded_content):
    started = start(api_client, seeded_content)
    question = started.json()["content"]["questions"][0]
    saved = api_client.put(
        save_url(started, question["id"]),
        {"selected_choice_id": question["choices"][0]["id"], "expected_revision": 0},
        format="json",
        HTTP_IDEMPOTENCY_KEY=str(uuid4()),
        **guest_headers(started),
    )
    assert saved.status_code == 200
    assert "feedback" not in saved.json()

    results_url = f"{SESSIONS_URL}{started.json()['id']}/results/"
    locked = api_client.get(results_url, **guest_headers(started))
    assert locked.status_code == 409
    assert locked.json()["code"] == "results_not_released"


def test_autosave_is_idempotent_and_revision_safe(api_client, seeded_content):
    started = start(api_client, seeded_content)
    question = started.json()["content"]["questions"][0]
    url = save_url(started, question["id"])
    key = str(uuid4())
    body = {"selected_choice_id": question["choices"][0]["id"], "expected_revision": 0}

    first = api_client.put(
        url,
        body,
        format="json",
        HTTP_IDEMPOTENCY_KEY=key,
        **guest_headers(started),
    )
    replay = api_client.put(
        url,
        body,
        format="json",
        HTTP_IDEMPOTENCY_KEY=key,
        **guest_headers(started),
    )
    assert first.status_code == replay.status_code == 200
    assert replay.json()["replayed"] is True
    assert Response.objects.get().revision == 1

    conflict_body = {"selected_choice_id": question["choices"][1]["id"], "expected_revision": 0}
    conflict = api_client.put(
        url,
        conflict_body,
        format="json",
        HTTP_IDEMPOTENCY_KEY=key,
        **guest_headers(started),
    )
    assert conflict.status_code == 409
    assert conflict.json()["code"] == "idempotency_conflict"

    stale = api_client.put(
        url,
        conflict_body,
        format="json",
        HTTP_IDEMPOTENCY_KEY=str(uuid4()),
        **guest_headers(started),
    )
    assert stale.status_code == 409
    assert stale.json()["code"] == "stale_revision"


def test_rejects_malformed_and_cross_question_answers(api_client, seeded_content):
    started = start(api_client, seeded_content)
    first, second = started.json()["content"]["questions"][:2]
    url = save_url(started, first["id"])
    body = {"selected_choice_id": second["choices"][0]["id"], "expected_revision": 0}

    missing_key = api_client.put(url, body, format="json", **guest_headers(started))
    assert missing_key.status_code == 400
    assert missing_key.json()["code"] == "invalid_idempotency_key"

    wrong_choice = api_client.put(
        url,
        body,
        format="json",
        HTTP_IDEMPOTENCY_KEY=str(uuid4()),
        **guest_headers(started),
    )
    assert wrong_choice.status_code == 400
    assert wrong_choice.json()["code"] == "invalid_answer"


def test_deadline_blocks_save_but_allows_idempotent_submit(api_client, seeded_content):
    started = start(api_client, seeded_content, time_limit_seconds=60)
    AssessmentSession.objects.filter(pk=started.json()["id"]).update(
        deadline_at=timezone.now() - timedelta(seconds=1)
    )
    question = started.json()["content"]["questions"][0]
    blocked = api_client.put(
        save_url(started, question["id"]),
        {"selected_choice_id": question["choices"][0]["id"], "expected_revision": 0},
        format="json",
        HTTP_IDEMPOTENCY_KEY=str(uuid4()),
        **guest_headers(started),
    )
    assert blocked.status_code == 409
    assert blocked.json()["code"] == "session_deadline_passed"

    submit_url = f"{SESSIONS_URL}{started.json()['id']}/submit/"
    first = api_client.post(submit_url, **guest_headers(started))
    replay = api_client.post(submit_url, **guest_headers(started))
    assert first.status_code == replay.status_code == 200
    assert first.json()["raw_correct"] == 0
    assert first.json()["raw_possible"] == 4
    assert replay.json()["replayed"] is True


def test_submit_scores_server_side_and_releases_explanations(api_client, seeded_content):
    started = start(api_client, seeded_content)
    session = AssessmentSession.objects.get(pk=started.json()["id"])
    snapshot = session.items.get().snapshot
    for question in snapshot["questions"]:
        correct = next(choice for choice in question["choices"] if choice["is_correct"])
        response = api_client.put(
            save_url(started, question["id"]),
            {"selected_choice_id": correct["id"], "expected_revision": 0},
            format="json",
            HTTP_IDEMPOTENCY_KEY=str(uuid4()),
            **guest_headers(started),
        )
        assert response.status_code == 200

    submitted = api_client.post(
        f"{SESSIONS_URL}{started.json()['id']}/submit/",
        **guest_headers(started),
    )
    assert submitted.status_code == 200
    assert submitted.json()["raw_correct"] == submitted.json()["raw_possible"] == 4
    assert submitted.json()["accuracy_percent"] == 100
    assert submitted.json()["score_label"] == "Practice accuracy"
    assert "not an official CELPIP score" in submitted.json()["disclaimer"]
    assert submitted.json()["outcomes"][0]["explanation"]


def test_unpublished_content_cannot_start(api_client, seeded_content):
    response = start(api_client, "does-not-exist")
    assert response.status_code == 400
    assert response.json()["code"] == "content_unavailable"
