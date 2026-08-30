"""Session recovery and heartbeat endpoints for resuming autosaved work."""
from datetime import timedelta
from uuid import uuid4

import pytest
from django.core.management import call_command
from django.utils import timezone

from apps.accounts.models import User
from apps.assessments.models import AssessmentSession

pytestmark = pytest.mark.django_db

SESSIONS_URL = "/api/v1/sessions/"
ME_SESSIONS_URL = "/api/v1/me/sessions/"


@pytest.fixture
def seeded_reading():
    call_command("seed_reading_content", verbosity=0)
    return "garden-plot-renewal"


@pytest.fixture
def learner(api_client):
    user = User.objects.create_user(identifier="recover-learner", password="secret1")
    api_client.force_authenticate(user)
    return user


def _start_reading(api_client, slug, **extra):
    return api_client.post(
        SESSIONS_URL,
        {"content_slug": slug, "mode": "practice"} | extra,
        format="json",
    )


def test_session_list_requires_an_account(api_client):
    assert api_client.get(ME_SESSIONS_URL).status_code == 401


def test_active_session_appears_with_resume_metadata(api_client, learner, seeded_reading):
    started = _start_reading(api_client, seeded_reading, time_limit_seconds=600)
    assert started.status_code == 201
    session_id = started.json()["id"]
    question = started.json()["content"]["questions"][0]

    saved = api_client.put(
        f"{SESSIONS_URL}{session_id}/responses/{question['id']}/",
        {"selected_choice_id": question["choices"][0]["id"], "expected_revision": 0},
        format="json",
        HTTP_IDEMPOTENCY_KEY=str(uuid4()),
    )
    assert saved.status_code == 200

    listing = api_client.get(ME_SESSIONS_URL).json()
    assert listing["count"] == 1
    row = listing["results"][0]
    assert row["id"] == session_id
    assert row["mode"] == "practice"
    assert row["state"] == "active"
    assert row["skill"] == "reading"
    assert row["title"]
    assert row["progress"] == {"answered": 1, "total": 4}
    assert row["launch_url"] == f"/reading/session/{session_id}"
    assert row["deadline_at"] is not None


def test_submitted_sessions_sort_after_active(api_client, learner, seeded_reading):
    first = _start_reading(api_client, seeded_reading, time_limit_seconds=600)
    second = _start_reading(api_client, seeded_reading, time_limit_seconds=600)
    submitted = api_client.post(f"{SESSIONS_URL}{second.json()['id']}/submit/")
    assert submitted.status_code == 200

    rows = api_client.get(ME_SESSIONS_URL).json()["results"]
    assert [row["id"] for row in rows] == [first.json()["id"], second.json()["id"]]
    assert rows[0]["state"] == "active"
    assert rows[1]["state"] == "submitted"


def test_filters_and_invalid_query(api_client, learner, seeded_reading):
    _start_reading(api_client, seeded_reading, time_limit_seconds=600)
    assert api_client.get(f"{ME_SESSIONS_URL}?skill=reading").json()["count"] == 1
    assert api_client.get(f"{ME_SESSIONS_URL}?skill=writing").json()["count"] == 0
    assert api_client.get(f"{ME_SESSIONS_URL}?state=submitted").json()["count"] == 0
    assert api_client.get(f"{ME_SESSIONS_URL}?mode=learn").json()["count"] == 0

    bad = api_client.get(f"{ME_SESSIONS_URL}?skill=rock-climbing")
    assert bad.status_code == 400
    assert bad.json()["code"] == "invalid_query"
    assert bad.json()["fields"] == {"skill": "rock-climbing"}


def test_writing_session_recovery_entry(api_client, learner):
    call_command("seed_writing_content", verbosity=0)
    started = api_client.post(
        SESSIONS_URL,
        {
            "content_slug": "email-noisy-renovation",
            "mode": "practice",
            "time_limit_seconds": 600,
        },
        format="json",
    )
    assert started.status_code == 201

    row = api_client.get(ME_SESSIONS_URL).json()["results"][0]
    assert row["mode"] == "practice"
    assert row["skill"] == "writing"
    assert row["launch_url"] == f"/writing/session/{row['id']}"
    assert row["progress"] == {"saved": False, "submitted": False}


def test_touch_requires_owner_and_updates_activity(api_client, learner, seeded_reading):
    started = _start_reading(api_client, seeded_reading, time_limit_seconds=600)
    session_id = started.json()["id"]
    AssessmentSession.objects.filter(pk=session_id).update(
        last_activity_at=timezone.now() - timedelta(days=2)
    )

    response = api_client.post(f"{SESSIONS_URL}{session_id}/touch/")
    assert response.status_code == 200
    body = response.json()
    assert body["session_id"] == session_id
    assert body["server_now"]
    assert "last_activity_at" in body
    fresh = AssessmentSession.objects.get(pk=session_id)
    assert fresh.last_activity_at > timezone.now() - timedelta(days=1)

    stranger = User.objects.create_user(identifier="touch-stranger", password="secret1")
    api_client.force_authenticate(stranger)
    denied = api_client.post(f"{SESSIONS_URL}{session_id}/touch/")
    assert denied.status_code == 403
    assert denied.json()["code"] == "session_access_denied"


def test_guest_touch_requires_token(api_client, seeded_reading):
    started = _start_reading(api_client, seeded_reading, time_limit_seconds=600)
    session_id = started.json()["id"]
    token = started.json()["guest_token"]

    assert api_client.post(f"{SESSIONS_URL}{session_id}/touch/").status_code == 403
    allowed = api_client.post(
        f"{SESSIONS_URL}{session_id}/touch/", HTTP_X_GUEST_TOKEN=token
    )
    assert allowed.status_code == 200


def test_touch_unknown_session_is_404(api_client, learner):
    response = api_client.post(f"{SESSIONS_URL}{uuid4()}/touch/")
    assert response.status_code == 404
