"""Speaking content, private recording, and submission security tests."""

from datetime import timedelta
from io import StringIO
from pathlib import Path
from uuid import uuid4

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.utils import timezone

from apps.accounts.models import User
from apps.assessments.models import AssessmentSession, SpeakingSubmission
from apps.assessments.storage import private_recording_storage
from apps.content.models import ContentItem, ContentVersion, Question, Skill, TaskType
from apps.content.services import SPEAKING_TASK_SPECS, validate_content_version

pytestmark = pytest.mark.django_db

SESSIONS_URL = "/api/v1/sessions/"
ADVICE_SLUG = "advice-first-canadian-winter"
SCENE_SLUG = "scene-winter-recreation-centre"


@pytest.fixture(autouse=True)
def isolated_recording_storage(tmp_path, monkeypatch):
    monkeypatch.setattr(private_recording_storage, "_location", str(tmp_path))
    private_recording_storage.__dict__.pop("base_location", None)
    private_recording_storage.__dict__.pop("location", None)
    yield tmp_path


@pytest.fixture
def speaking_bank():
    call_command("seed_speaking_content", verbosity=0)
    return ADVICE_SLUG


def start(api_client, slug=ADVICE_SLUG, mode="practice"):
    return api_client.post(
        SESSIONS_URL,
        {"content_slug": slug, "mode": mode, "time_limit_seconds": 120},
        format="json",
    )


def guest_headers(started):
    return {"HTTP_X_GUEST_TOKEN": started.json()["guest_token"]}


def speaking_url(started):
    return f"{SESSIONS_URL}{started.json()['id']}/speaking/"


def recording(data=b"\x1aE\xdf\xa3" + b"practice-audio" * 20, mime="audio/webm"):
    return SimpleUploadedFile("response.webm", data, content_type=mime)


def upload(api_client, started, *, expected=0, key=None, audio=None, duration=45_000):
    return api_client.put(
        speaking_url(started),
        {
            "audio": audio or recording(),
            "duration_ms": duration,
            "expected_revision": expected,
        },
        format="multipart",
        HTTP_IDEMPOTENCY_KEY=key or str(uuid4()),
        **guest_headers(started),
    )


def test_seed_is_idempotent_complete_and_original():
    first, second = StringIO(), StringIO()
    call_command("seed_speaking_content", stdout=first)
    call_command("seed_speaking_content", stdout=second)

    assert "created 16" in first.getvalue()
    assert "created 0" in second.getvalue()
    assert TaskType.objects.filter(skill=Skill.SPEAKING).count() == 8
    assert ContentItem.objects.filter(task_type__skill=Skill.SPEAKING).count() == 16
    assert ContentVersion.objects.filter(
        item__task_type__skill=Skill.SPEAKING, status="published"
    ).count() == 16
    assert Question.objects.filter(
        content_version__item__task_type__skill=Skill.SPEAKING
    ).count() == 0
    assert not ContentVersion.objects.filter(
        item__task_type__skill=Skill.SPEAKING, reviewer_id=None
    ).exists()
    assert not ContentItem.objects.filter(
        task_type__skill=Skill.SPEAKING, provenance=""
    ).exists()


def test_all_task_timings_and_structures_match_official_format(speaking_bank):
    versions = ContentVersion.objects.filter(
        item__task_type__skill=Skill.SPEAKING, status="published"
    ).select_related("item__task_type")
    assert versions.count() == 16
    for version in versions:
        kind, prep, response = SPEAKING_TASK_SPECS[version.item.task_type_id]
        stimulus = version.stimulus
        assert stimulus["task_kind"] == kind
        assert stimulus["prep_seconds"] == prep
        assert stimulus["response_seconds"] == response
        assert validate_content_version(version) == []
        if kind in {"scene", "predictions", "unusual"}:
            assert stimulus["image_url"].startswith("/speaking/")
        if kind == "compare_persuade":
            assert [stage["seconds"] for stage in stimulus["prep_stages"]] == [60, 60]
            assert len(stimulus["initial_options"]) == 2
            assert stimulus["competing_option"]["label"]


def test_catalog_filter_detail_and_practice_guidance_hiding(api_client, speaking_bank):
    catalog = api_client.get("/api/v1/content/speaking/")
    filtered = api_client.get(
        "/api/v1/content/speaking/", {"task_type": "speaking_unusual"}
    )
    detail = api_client.get(f"/api/v1/content/speaking/{SCENE_SLUG}/")
    assert catalog.status_code == 200 and catalog.json()["count"] == 16
    assert len(filtered.json()["results"]) == 2
    assert detail.status_code == 200
    assert detail.json()["stimulus"]["image_url"].startswith("/speaking/")

    started = start(api_client)
    resumed = api_client.get(speaking_url(started), **guest_headers(started))
    assert resumed.status_code == 200
    assert "guidance" not in resumed.json()["content"]["stimulus"]
    assert resumed.json()["submission"] is None
    assert [item["label"] for item in resumed.json()["rubric"]["dimensions"]] == [
        "Content/Coherence",
        "Vocabulary",
        "Listenability",
        "Task Fulfillment",
    ]


def test_speaking_validation_rejects_malformed_prompt(speaking_bank):
    task_type = TaskType.objects.get(pk="speaking_scene")
    item = ContentItem.objects.create(
        slug="malformed-speaking-test",
        task_type=task_type,
        title="Malformed prompt",
        topic="Testing",
        difficulty=1,
        estimated_level=5,
        provenance="Original automated-test fixture.",
    )
    version = ContentVersion.objects.create(
        item=item,
        version=1,
        instructions="Speak.",
        stimulus={
            "type": "wrong",
            "task_kind": "advice",
            "scenario": "",
            "prompt": "",
            "prep_seconds": 99,
            "response_seconds": 99,
        },
    )
    codes = {issue.code for issue in validate_content_version(version)}
    assert {
        "invalid_speaking_stimulus_type",
        "speaking_task_kind_mismatch",
        "missing_speaking_scenario",
        "missing_speaking_prompt",
        "invalid_speaking_prep_time",
        "invalid_speaking_response_time",
        "missing_speaking_image",
    } <= codes


def test_guest_access_and_private_payload(api_client, speaking_bank):
    started = start(api_client)
    assert api_client.get(speaking_url(started)).status_code == 403
    saved = upload(api_client, started)
    assert saved.status_code == 200
    payload = saved.json()
    assert payload["revision"] == 1
    assert payload["audio_url"].endswith("/speaking/audio/")
    assert "private_media" not in str(payload)
    assert "audio" not in payload or "audio_url" in payload


def test_authenticated_owner_is_enforced(api_client, speaking_bank):
    owner = User.objects.create_user(identifier="speaker-owner", password="secret1")
    api_client.force_authenticate(owner)
    started = start(api_client)
    stranger = User.objects.create_user(identifier="speaker-stranger", password="secret1")
    api_client.force_authenticate(stranger)
    assert api_client.get(speaking_url(started)).status_code == 403


def test_spoofed_format_and_oversize_are_rejected(api_client, speaking_bank):
    started = start(api_client)
    spoof = upload(
        api_client,
        started,
        audio=recording(data=b"not-webm-at-all", mime="audio/webm"),
    )
    assert spoof.status_code == 400
    assert spoof.json()["code"] == "invalid_recording"

    huge = recording(data=b"\x1aE\xdf\xa3" + b"x" * (15 * 1024 * 1024), mime="audio/webm")
    oversized = upload(api_client, started, audio=huge)
    assert oversized.status_code == 400
    assert oversized.json()["code"] == "recording_too_large"


def test_revision_idempotency_and_replacement_cleanup(
    api_client, speaking_bank, django_capture_on_commit_callbacks
):
    started = start(api_client)
    key = str(uuid4())
    first = upload(api_client, started, key=key)
    original_path = Path(SpeakingSubmission.objects.get().audio.path)
    replay = upload(api_client, started, key=key)
    assert first.status_code == replay.status_code == 200
    assert replay.json()["replayed"] is True
    assert SpeakingSubmission.objects.get().revision == 1

    conflict = upload(api_client, started, key=key, audio=recording(data=b"\x1aE\xdf\xa3different"))
    assert conflict.status_code == 409
    assert conflict.json()["code"] == "idempotency_conflict"
    stale = upload(api_client, started, expected=0)
    assert stale.status_code == 409 and stale.json()["code"] == "stale_revision"

    with django_capture_on_commit_callbacks(execute=True):
        replaced = upload(
            api_client,
            started,
            expected=1,
            audio=recording(data=b"\x1aE\xdf\xa3replacement"),
        )
    assert replaced.status_code == 200
    assert SpeakingSubmission.objects.get().revision == 2
    assert not original_path.exists()


def test_parent_deletion_removes_private_recording(api_client, speaking_bank):
    started = start(api_client)
    assert upload(api_client, started).status_code == 200
    recording_path = Path(SpeakingSubmission.objects.get().audio.path)
    assert recording_path.exists()

    AssessmentSession.objects.get(pk=started.json()["id"]).delete()

    assert not recording_path.exists()


def test_private_audio_range_head_and_unauthorized(api_client, speaking_bank):
    started = start(api_client)
    upload(api_client, started)
    audio_url = f"{speaking_url(started)}audio/"
    assert api_client.get(audio_url).status_code == 403

    ranged = api_client.get(
        audio_url, HTTP_RANGE="bytes=0-7", **guest_headers(started)
    )
    assert ranged.status_code == 206
    assert ranged["Content-Range"].startswith("bytes 0-7/")
    assert ranged["Cache-Control"] == "private, no-store"
    assert ranged["X-Content-Type-Options"] == "nosniff"
    assert len(b"".join(ranged.streaming_content)) == 8

    suffix = api_client.get(
        audio_url, HTTP_RANGE="bytes=-5", **guest_headers(started)
    )
    assert suffix.status_code == 206
    assert len(b"".join(suffix.streaming_content)) == 5
    invalid = api_client.get(
        audio_url, HTTP_RANGE="bytes=99999-", **guest_headers(started)
    )
    assert invalid.status_code == 416
    assert invalid["Content-Range"].startswith("bytes */")
    head = api_client.head(audio_url, **guest_headers(started))
    assert head.status_code == 200 and int(head["Content-Length"]) > 0


def test_upload_after_deadline_submit_replay_and_immutability(api_client, speaking_bank):
    started = start(api_client)
    AssessmentSession.objects.filter(pk=started.json()["id"]).update(
        deadline_at=timezone.now() - timedelta(seconds=1)
    )
    saved = upload(api_client, started)
    assert saved.status_code == 200
    submit_url = f"{speaking_url(started)}submit/"
    first = api_client.post(submit_url, **guest_headers(started))
    replay = api_client.post(submit_url, **guest_headers(started))
    assert first.status_code == replay.status_code == 200
    assert replay.json()["replayed"] is True
    assert first.json()["estimated_level"] is None
    assert first.json()["transcript"] is None
    assert "not an official CELPIP" in first.json()["disclaimer"]

    blocked = upload(api_client, started, expected=1)
    assert blocked.status_code == 409
    submission = SpeakingSubmission.objects.get()
    submission.duration_ms += 1
    with pytest.raises(ValidationError, match="immutable"):
        submission.save()
    with pytest.raises(ValidationError, match="immutable"):
        submission.delete()


def test_blank_submit_and_objective_submit_are_rejected(api_client, speaking_bank):
    started = start(api_client)
    missing = api_client.post(
        f"{speaking_url(started)}submit/", **guest_headers(started)
    )
    assert missing.status_code == 400
    assert missing.json()["code"] == "missing_recording"
    wrong = api_client.post(
        f"{SESSIONS_URL}{started.json()['id']}/submit/", **guest_headers(started)
    )
    assert wrong.status_code == 400 and wrong.json()["code"] == "wrong_skill"


def test_session_snapshot_stays_frozen(api_client, speaking_bank):
    started = start(api_client, slug=SCENE_SLUG)
    session = AssessmentSession.objects.get(pk=started.json()["id"])
    frozen = session.items.get().snapshot["stimulus"]["prompt"]
    version = ContentVersion.objects.get(item__slug=SCENE_SLUG, status="published")
    ContentVersion.objects.filter(pk=version.pk).update(
        stimulus=version.stimulus | {"prompt": "Database text changed later."}
    )
    resumed = api_client.get(speaking_url(started), **guest_headers(started))
    assert resumed.json()["content"]["stimulus"]["prompt"] == frozen
