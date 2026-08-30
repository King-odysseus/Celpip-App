"""Private-path validation, playback policy, and signed stream access."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from django.conf import settings
from django.core import signing
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import PreferredAudioProvider
from apps.assessments.models import AssessmentSession, SessionMode, SessionState

from .models import (
    AudioRendition,
    MediaAsset,
    MediaPlaybackGrant,
    MediaStatus,
    RenditionProvider,
)

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
    selected_provider: str


@dataclass(frozen=True)
class PlayableAudioSource:
    """The concrete file chosen for one playback, canonical or a rendition.

    ``provider`` is a :class:`PreferredAudioProvider` value (``local`` for the
    canonical recording; ``openai``/``azure`` for a rendition). ``rendition_id``
    is ``None`` for the canonical source. Every field mirrors the underlying
    row so the stream path never needs a second lookup to serve bytes.
    """

    canonical_asset: MediaAsset
    provider: str
    storage_key: str
    mime_type: str
    byte_size: int
    checksum_sha256: str
    rendition_id: object | None = None


def private_media_path(storage_key: str) -> Path:
    root = Path(settings.PRIVATE_MEDIA_ROOT).resolve()
    path = (root / storage_key).resolve()
    if root not in path.parents:
        raise MediaUnavailable("Invalid private media path.")
    return path


def ensure_playable_file(asset: MediaAsset | PlayableAudioSource) -> Path:
    """Cheap on-disk guard for the streaming hot path.

    Full checksum integrity is validated at seed and at grant time. Re-hashing
    the whole file on every byte-range request would let any holder of a valid
    token amplify CPU/IO, so the stream path only confirms the file still exists
    at the expected size. Accepts any object exposing ``storage_key`` and
    ``byte_size`` (a :class:`MediaAsset` or a :class:`PlayableAudioSource`).
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


def _integrity_ok(storage_key: str, byte_size: int, checksum_sha256: str) -> bool:
    """Strict on-disk validation: safe path, exact size, and matching checksum."""
    try:
        path = private_media_path(storage_key)
    except MediaUnavailable:
        return False
    if not path.is_file() or path.stat().st_size != byte_size:
        return False
    return file_checksum(path) == checksum_sha256


def _local_source(asset: MediaAsset) -> PlayableAudioSource | None:
    """Return a validated canonical (local) source, or None if unusable.

    Never raises and never surfaces why a candidate was rejected: callers treat
    a None result as "fall through to the next provider".
    """
    if asset.status != MediaStatus.READY:
        return None
    if not _integrity_ok(asset.storage_key, asset.byte_size, asset.checksum_sha256):
        return None
    return PlayableAudioSource(
        canonical_asset=asset,
        provider=PreferredAudioProvider.LOCAL,
        storage_key=asset.storage_key,
        mime_type=asset.mime_type,
        byte_size=asset.byte_size,
        checksum_sha256=asset.checksum_sha256,
        rendition_id=None,
    )


def _source_from_rendition(
    asset: MediaAsset, rendition: AudioRendition
) -> PlayableAudioSource | None:
    """Return a validated rendition source, or None if it fails integrity."""
    if not _integrity_ok(
        rendition.storage_key, rendition.byte_size, rendition.checksum_sha256
    ):
        return None
    return PlayableAudioSource(
        canonical_asset=asset,
        provider=rendition.provider,
        storage_key=rendition.storage_key,
        mime_type=rendition.mime_type,
        byte_size=rendition.byte_size,
        checksum_sha256=rendition.checksum_sha256,
        rendition_id=rendition.id,
    )


def _rendition_source(asset: MediaAsset, provider: str) -> PlayableAudioSource | None:
    """Return a validated READY rendition for ``provider``, or None."""
    rendition = AudioRendition.objects.filter(
        canonical_asset=asset, provider=provider, status=MediaStatus.READY
    ).first()
    if rendition is None:
        return None
    return _source_from_rendition(asset, rendition)


def _candidate_source(asset: MediaAsset, provider: str) -> PlayableAudioSource | None:
    if provider == PreferredAudioProvider.LOCAL:
        return _local_source(asset)
    if provider in (RenditionProvider.OPENAI, RenditionProvider.AZURE):
        return _rendition_source(asset, provider)
    return None


def select_audio_source(
    asset: MediaAsset, user=None, preferred: str | None = None
) -> PlayableAudioSource:
    """Choose the playback source for ``asset`` honouring the learner's wish.

    An explicit ``preferred`` wins; otherwise an authenticated learner's stored
    ``preferred_audio_provider`` is used. Guests (and "automatic") fall back to
    the configured order. Ordering is: a non-automatic preference first, then
    ``settings.LISTENING_TTS_PROVIDER_ORDER`` (de-duplicated), with the canonical
    local recording always tried last. Missing or integrity-failing candidates
    fall through. Raises :class:`MediaUnavailable` when nothing is playable.
    """
    if preferred is None and getattr(user, "is_authenticated", False):
        profile = getattr(user, "profile", None)
        if profile is not None:
            preferred = profile.preferred_audio_provider

    order: list[str] = []
    # A non-automatic explicit/profile preference is always tried first.
    if preferred and preferred != PreferredAudioProvider.AUTOMATIC:
        order.append(preferred)

    # The automatic fallback chain follows the configured order, de-duplicated,
    # with the canonical local recording always the terminal fallback.
    fallback: list[str] = []
    for provider in settings.LISTENING_TTS_PROVIDER_ORDER:
        if provider != PreferredAudioProvider.LOCAL and provider not in fallback:
            fallback.append(provider)
    fallback.append(PreferredAudioProvider.LOCAL)
    for provider in fallback:
        if provider not in order:
            order.append(provider)

    for provider in order:
        source = _candidate_source(asset, provider)
        if source is not None:
            return source
    raise MediaUnavailable("This audio is unavailable.")


def _resolve_exact_source(
    asset: MediaAsset, provider, rendition_id
) -> PlayableAudioSource | None:
    """Re-resolve the exact source named in a token, with no fallback.

    The provider and rendition id must match a currently-valid file exactly;
    any mismatch or integrity failure returns None so the caller can reject the
    request rather than silently serving a different rendition.
    """
    if provider == PreferredAudioProvider.LOCAL:
        if rendition_id is not None:
            return None
        return _local_source(asset)
    if provider in (RenditionProvider.OPENAI, RenditionProvider.AZURE):
        if not rendition_id:
            return None
        rendition = AudioRendition.objects.filter(
            pk=rendition_id,
            canonical_asset=asset,
            provider=provider,
            status=MediaStatus.READY,
        ).first()
        if rendition is None:
            return None
        return _source_from_rendition(asset, rendition)
    return None


@transaction.atomic
def grant_audio_access(
    *, session: AssessmentSession, asset: MediaAsset, user=None
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
        locked_session.mode in (SessionMode.PRACTICE, SessionMode.MOCK)
        and locked_session.state == SessionState.ACTIVE
    )
    if limited and grant.grants_issued >= 1:
        raise PlaybackLimitReached("Timed sessions allow one audio playback.")
    # Choose the concrete file to serve. The playback grant and the streamed
    # URL stay keyed on the canonical asset; only the bytes may differ.
    source = select_audio_source(asset, user=user)

    grant.grants_issued += 1
    grant.last_granted_at = timezone.now()
    grant.save(update_fields=["grants_issued", "last_granted_at"])

    token = signing.dumps(
        {
            "scope": "session",
            "asset_id": str(asset.pk),
            "session_id": str(locked_session.pk),
            "provider": source.provider,
            "rendition_id": (
                str(source.rendition_id) if source.rendition_id else None
            ),
        },
        salt=TOKEN_SALT,
        compress=True,
    )
    remaining = max(0, 1 - grant.grants_issued) if limited else None
    return AudioAccess(
        url=f"/api/v1/media/audio/{asset.pk}/stream/?token={token}",
        expires_in_seconds=TOKEN_MAX_AGE_SECONDS,
        plays_remaining=remaining,
        selected_provider=source.provider,
    )


def verify_stream_token(*, asset_id, token: str) -> PlayableAudioSource:
    try:
        payload = signing.loads(
            token,
            salt=TOKEN_SALT,
            max_age=TOKEN_MAX_AGE_SECONDS,
        )
    except signing.BadSignature as exc:
        raise MediaAccessError("The audio link is invalid or expired.") from exc
    if payload.get("scope") != "session":
        raise MediaAccessError("The audio link is invalid or expired.")
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
    # Re-resolve exactly what the token names: the exact provider and rendition,
    # with no fallback. A tampered or now-missing source fails closed.
    source = _resolve_exact_source(
        asset, payload.get("provider"), payload.get("rendition_id")
    )
    if source is None:
        raise MediaUnavailable("This audio failed its integrity check.")
    return source
