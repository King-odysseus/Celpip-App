"""Listening seeding, private audio, playback policy, and transcript release."""
from io import StringIO
from uuid import uuid4

import pytest
from django.core.management import call_command

from apps.content.models import Choice, ContentItem, ContentVersion, Question, TaskType
from apps.media_assets.models import MediaAsset, MediaPlaybackGrant
from apps.media_assets.services import validate_audio_asset

pytestmark = pytest.mark.django_db

SESSIONS_URL = "/api/v1/sessions/"


@pytest.fixture
def listening_bank():
    call_command("seed_listening_content", verbosity=0)
    return "apartment-heating-plan"


def start(api_client, slug, mode="practice"):
    return api_client.post(
        SESSIONS_URL,
        {"content_slug": slug, "mode": mode, "time_limit_seconds": 900},
        format="json",
    )


def guest_headers(started):
    return {"HTTP_X_GUEST_TOKEN": started.json()["guest_token"]}


def test_listening_seed_is_idempotent_complete_and_integrity_checked():
    first = StringIO()
    second = StringIO()
    call_command("seed_listening_content", stdout=first)
    call_command("seed_listening_content", stdout=second)

    assert "created 6" in first.getvalue()
    assert "created 0" in second.getvalue()
    assert TaskType.objects.filter(skill="listening").count() == 6
    assert ContentItem.objects.filter(task_type__skill="listening").count() == 6
    assert ContentVersion.objects.filter(item__task_type__skill="listening").count() == 6
    listening_questions = Question.objects.filter(
        content_version__item__task_type__skill="listening"
    )
    listening_choices = Choice.objects.filter(
        question__content_version__item__task_type__skill="listening"
    )
    assert listening_questions.count() == 18
    assert listening_choices.count() == 72
    assert MediaAsset.objects.count() == 6
    for asset in MediaAsset.objects.all():
        assert asset.duration_ms >= 60_000
        assert validate_audio_asset(asset) == []


def test_listening_catalog_and_session_never_leak_transcript(api_client, listening_bank):
    task_types = api_client.get("/api/v1/content/task-types/?skill=listening")
    catalog = api_client.get("/api/v1/content/listening/")
    detail = api_client.get(f"/api/v1/content/listening/{listening_bank}/")
    started = start(api_client, listening_bank)

    assert task_types.status_code == 200
    assert len(task_types.json()) == 6
    assert catalog.status_code == 200
    assert catalog.json()["count"] == 6
    assert detail.status_code == 200
    assert started.status_code == 201
    assert started.json()["content"]["skill"] == "listening"
    assert started.json()["audio"]["playback_policy"] == "one_play"
    for payload in (catalog.json(), detail.json(), started.json()):
        assert "transcript" not in str(payload).lower()
        assert "is_correct" not in str(payload)


def test_practice_audio_grants_once_and_streams_private_ranges(api_client, listening_bank):
    started = start(api_client, listening_bank)
    asset_id = started.json()["audio"]["asset_id"]
    access_url = f"{SESSIONS_URL}{started.json()['id']}/media/{asset_id}/access/"

    no_token = api_client.post(access_url)
    first = api_client.post(access_url, **guest_headers(started))
    second = api_client.post(access_url, **guest_headers(started))

    assert no_token.status_code == 403
    assert first.status_code == 200
    assert first.json()["plays_remaining"] == 0
    assert second.status_code == 409
    assert second.json()["code"] == "playback_limit_reached"
    assert MediaPlaybackGrant.objects.get().grants_issued == 1

    ranged = api_client.get(first.json()["url"], HTTP_RANGE="bytes=0-31")
    assert ranged.status_code == 206
    assert ranged["Content-Type"] == "audio/wav"
    assert ranged["Content-Range"].startswith("bytes 0-31/")
    assert len(b"".join(ranged.streaming_content)) == 32

    tampered = api_client.get(first.json()["url"] + "x")
    assert tampered.status_code == 403


def test_audio_from_another_set_is_denied(api_client, listening_bank):
    started = start(api_client, listening_bank)
    other_asset = MediaAsset.objects.exclude(pk=started.json()["audio"]["asset_id"]).first()
    access_url = (
        f"{SESSIONS_URL}{started.json()['id']}/media/{other_asset.id}/access/"
    )

    response = api_client.post(access_url, **guest_headers(started))
    assert response.status_code == 403
    assert response.json()["code"] == "media_access_denied"


def test_learn_allows_replay_and_releases_transcript_after_answer(api_client, listening_bank):
    started = start(api_client, listening_bank, mode="learn")
    asset_id = started.json()["audio"]["asset_id"]
    access_url = f"{SESSIONS_URL}{started.json()['id']}/media/{asset_id}/access/"
    for _ in range(2):
        granted = api_client.post(access_url, **guest_headers(started))
        assert granted.status_code == 200
        assert granted.json()["plays_remaining"] is None

    question = started.json()["content"]["questions"][0]
    saved = api_client.put(
        f"{SESSIONS_URL}{started.json()['id']}/responses/{question['id']}/",
        {
            "selected_choice_id": question["choices"][0]["id"],
            "expected_revision": 0,
        },
        format="json",
        HTTP_IDEMPOTENCY_KEY=str(uuid4()),
        **guest_headers(started),
    )
    assert saved.status_code == 200
    assert "transcript" in saved.json()["feedback"]
    assert len(saved.json()["feedback"]["transcript"]) > 500


def test_practice_releases_transcript_only_after_submission(api_client, listening_bank):
    started = start(api_client, listening_bank)
    before = api_client.get(
        f"{SESSIONS_URL}{started.json()['id']}/results/",
        **guest_headers(started),
    )
    assert before.status_code == 409

    submitted = api_client.post(
        f"{SESSIONS_URL}{started.json()['id']}/submit/",
        **guest_headers(started),
    )
    assert submitted.status_code == 200
    assert "transcript" in submitted.json()
    assert "not an official CELPIP score" in submitted.json()["disclaimer"]
