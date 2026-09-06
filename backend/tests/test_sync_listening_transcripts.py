"""The sync_listening_transcripts command refreshes stored scripts without audio."""
from io import StringIO

import pytest
from django.core.management import call_command

from apps.content.management.commands.seed_listening_content import LISTENING_SETS
from apps.content.models import ContentItem, ContentVersion, TaskType
from apps.media_assets.models import MediaAsset, MediaStatus

pytestmark = pytest.mark.django_db


def _spec(slug):
    return next(s for s in LISTENING_SETS if s["slug"] == slug)


def _make_listening_item(slug):
    task_type = TaskType.objects.create(
        code="listening_problem_solving",
        skill="listening",
        title="Problem Solving",
        part_number=1,
        description="Test listening task",
    )
    item = ContentItem.objects.create(
        slug=slug,
        task_type=task_type,
        title="Test",
        topic="Test",
        difficulty=1,
        estimated_level=5,
        provenance="test",
    )
    return ContentVersion.objects.create(
        item=item,
        version=1,
        instructions="Test instructions",
        stimulus={"type": "audio_context"},
    )


def _make_asset(version, *, transcript, speaker_genders=None):
    return MediaAsset.objects.create(
        content_version=version,
        storage_key=f"listening/{version.item.slug}.wav",
        mime_type="audio/wav",
        byte_size=1000,
        duration_ms=45000,
        checksum_sha256="a" * 64,
        transcript=transcript,
        speaker_genders=speaker_genders,
        provenance="Original repository script; locally synthesized.",
        status=MediaStatus.READY,
    )


def test_sync_updates_stale_transcript_and_genders_without_touching_audio():
    target = _spec("weekend-market-produce-shortage")
    version = _make_listening_item(target["slug"])
    asset = _make_asset(
        version,
        transcript="Priya: The produce distributor just emailed that their main truck broke down.",
        speaker_genders=None,
    )
    original_checksum = asset.checksum_sha256
    original_provenance = asset.provenance

    call_command("sync_listening_transcripts", "--slug", target["slug"], verbosity=0)

    asset.refresh_from_db()
    assert asset.transcript == target["transcript"]
    assert asset.transcript.startswith("Priya: Tom, it's Priya at the market-and-café.")
    assert asset.speaker_genders == target["speaker_genders"]
    # The script moved forward; the recording and its metadata did not.
    assert asset.checksum_sha256 == original_checksum
    assert asset.provenance == original_provenance


def test_sync_is_idempotent():
    target = _spec("weekend-market-produce-shortage")
    version = _make_listening_item(target["slug"])
    _make_asset(
        version,
        transcript=target["transcript"],
        speaker_genders=target["speaker_genders"],
    )

    out = StringIO()
    call_command("sync_listening_transcripts", "--slug", target["slug"], stdout=out)

    assert "updated=0" in out.getvalue()
    assert "unchanged=1" in out.getvalue()


def test_sync_updates_transcript_and_keeps_absent_genders_none():
    # v2/v3 specs carry no speaker_genders; the field lands on None like the seed.
    target = _spec("office-printer-repair")
    version = _make_listening_item(target["slug"])
    asset = _make_asset(version, transcript="stale transcript", speaker_genders=None)

    call_command("sync_listening_transcripts", "--slug", target["slug"], verbosity=0)

    asset.refresh_from_db()
    assert asset.transcript == target["transcript"]
    assert asset.speaker_genders is None


def test_sync_flags_asset_not_in_manifest_without_changing_it():
    version = _make_listening_item("made-up-listening-slug")
    asset = _make_asset(version, transcript="orphaned transcript")

    out = StringIO()
    call_command(
        "sync_listening_transcripts",
        "--slug",
        "made-up-listening-slug",
        stdout=out,
    )

    asset.refresh_from_db()
    assert "missing=1" in out.getvalue()
    assert asset.transcript == "orphaned transcript"


def test_dry_run_counts_would_update_and_writes_nothing():
    target = _spec("weekend-market-produce-shortage")
    version = _make_listening_item(target["slug"])
    stale = "Priya: The produce distributor just emailed that their main truck broke down."
    asset = _make_asset(version, transcript=stale)

    out = StringIO()
    call_command(
        "sync_listening_transcripts",
        "--slug",
        target["slug"],
        "--dry-run",
        stdout=out,
    )

    assert "would update transcript" in out.getvalue()
    assert "1 would update" in out.getvalue()
    asset.refresh_from_db()
    assert asset.transcript == stale
