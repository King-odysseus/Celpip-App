"""Private-path validation, playback policy, and signed stream access."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from django.conf import settings
from django.core import signing
from django.db import transaction
from django.utils import timezone

from apps.assessments.models import AssessmentSession, SessionMode, SessionState

from .models import MediaAsset, MediaPlaybackGrant, MediaStatus

TOKEN_SALT = "celpip.private-audio.v1"
TOKEN_MAX_AGE_SECONDS = 10 * 60


class MediaAccessError(Exception):
    code = "media_access_denied"


class PlaybackLimitReached(MediaAccessError):
    code = "playback_limit_reached"


class MediaUnavailable(MediaAccessError):
    code = "media_unavailable"


@dataclass(frozen=True)
class AudioAccess:
    url: str
    expires_in_seconds: int
    plays_remaining: int | None


def private_media_path(storage_key: str) -> Path:
    root = Path(settings.PRIVATE_MEDIA_ROOT).resolve()
    path = (root / storage_key).resolve()
    if root not in path.parents:
        raise MediaUnavailable("Invalid private media path.")
    return path


def ensure_playable_file(asset: MediaAsset) -> Path:
    """Cheap on-disk guard for the streaming hot path.

    Full checksum integrity is validated at seed and at grant time. Re-hashing
    the whole file on every byte-range request would let any holder of a valid
    token amplify CPU/IO, so the stream path only confirms the file still exists
    at the expected size.
    """
    path = private_media_path(asset.storage_key)
    if not path.is_file() or path.stat().st_size != asset.byte_size:
        raise MediaUnavailable("This audio is unavailable.")
    return path


def file_checksum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as media_file:
        for chunk in iter(lambda: media_file.read(64 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_audio_asset(asset: MediaAsset) -> list[str]:
    issues = []
    if asset.mime_type not in {"audio/wav", "audio/mpeg"}:
        issues.append("Only WAV or MP3 audio is supported.")
    try:
        path = private_media_path(asset.storage_key)
    except MediaUnavailable as exc:
        return [str(exc)]
    if not path.is_file():
        issues.append("Private audio file is missing.")
        return issues
    if path.stat().st_size != asset.byte_size:
        issues.append("Stored byte size does not match metadata.")
    if file_checksum(path) != asset.checksum_sha256:
        issues.append("Stored checksum does not match metadata.")
    if not asset.transcript.strip():
        issues.append("A reviewed transcript is required.")
    if not asset.provenance.strip():
        issues.append("Audio provenance is required.")
    return issues


@transaction.atomic
def grant_audio_access(
    *, session: AssessmentSession, asset: MediaAsset
) -> AudioAccess:
    locked_session = AssessmentSession.objects.select_for_update().get(pk=session.pk)
    if asset.status != MediaStatus.READY or validate_audio_asset(asset):
        raise MediaUnavailable("This audio is not ready for playback.")
    if not locked_session.items.filter(content_version=asset.content_version).exists():
        raise MediaAccessError("Audio is not part of this assessment session.")

    grant, _ = MediaPlaybackGrant.objects.select_for_update().get_or_create(
        session=locked_session,
        asset=asset,
    )
    limited = (
        locked_session.mode == SessionMode.PRACTICE
        and locked_session.state == SessionState.ACTIVE
    )
    if limited and grant.grants_issued >= 1:
        raise PlaybackLimitReached("Timed Practice allows one audio playback.")
    grant.grants_issued += 1
    grant.last_granted_at = timezone.now()
    grant.save(update_fields=["grants_issued", "last_granted_at"])

    token = signing.dumps(
        {"asset_id": str(asset.pk), "session_id": str(locked_session.pk)},
        salt=TOKEN_SALT,
        compress=True,
    )
    remaining = max(0, 1 - grant.grants_issued) if limited else None
    return AudioAccess(
        url=f"/api/v1/media/audio/{asset.pk}/stream/?token={token}",
        expires_in_seconds=TOKEN_MAX_AGE_SECONDS,
        plays_remaining=remaining,
    )


def verify_stream_token(*, asset_id, token: str) -> MediaAsset:
    try:
        payload = signing.loads(
            token,
            salt=TOKEN_SALT,
            max_age=TOKEN_MAX_AGE_SECONDS,
        )
    except signing.BadSignature as exc:
        raise MediaAccessError("The audio link is invalid or expired.") from exc
    if payload.get("asset_id") != str(asset_id):
        raise MediaAccessError("The audio link does not match this asset.")
    asset = MediaAsset.objects.filter(pk=asset_id, status=MediaStatus.READY).first()
    if not asset:
        raise MediaUnavailable("This audio is unavailable.")
    if not MediaPlaybackGrant.objects.filter(
        session_id=payload.get("session_id"),
        asset=asset,
    ).exists():
        raise MediaAccessError("No playback grant exists for this audio.")
    if validate_audio_asset(asset):
        raise MediaUnavailable("This audio failed its integrity check.")
    return asset
