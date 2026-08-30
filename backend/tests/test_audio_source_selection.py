"""Session playback source selection, token binding, and integrity.

These tests exercise the provider-aware selection layer in
``apps.media_assets.services``: which concrete file (canonical local recording
or a per-provider rendition) is chosen for a playback, how that choice is bound
into the signed stream token, and how the stream path re-resolves it with no
fallback so a tampered or missing source fails closed.
"""
from __future__ import annotations

import io
import wave

import pytest
from django.core import signing
from django.core.management import call_command

from apps.accounts.models import LearnerProfile, PreferredAudioProvider, User
from apps.content.listening_seed_data import LISTENING_SETS as LISTENING_SETS_BASE
from apps.content.listening_seed_data_v2 import LISTENING_SETS as LISTENING_SETS_V2
from apps.media_assets.models import (
    AudioRendition,
    MediaAsset,
    MediaPlaybackGrant,
    MediaStatus,
)
from apps.media_assets.services import (
    TOKEN_SALT,
    MediaAccessError,
    MediaUnavailable,
    PlaybackLimitReached,
    file_checksum,
    grant_audio_access,
    private_media_path,
    select_audio_source,
    verify_stream_token,
)

pytestmark = pytest.mark.django_db

SESSIONS_URL = "/api/v1/sessions/"
APT_SLUG = "apartment-heating-plan"
LISTENING_SETS = LISTENING_SETS_BASE + LISTENING_SETS_V2


def make_wav(ms: int, *, frame_rate: int = 16000, sample: bytes = b"\x01\x00") -> bytes:
    frames = int(frame_rate * ms / 1000)
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as writer:
        writer.setnchannels(1)
        writer.setsampwidth(2)
        writer.setframerate(frame_rate)
        writer.writeframes(sample * frames)
    return buffer.getvalue()


@pytest.fixture
def isolated_listening(tmp_path, settings):
    """Seed Listening content into an isolated private-media root."""
    settings.PRIVATE_MEDIA_ROOT = tmp_path
    settings.LISTENING_TTS_PROVIDER_ORDER = ["openai", "azure", "local"]
    listening_dir = tmp_path / "listening"
    listening_dir.mkdir()
    for spec in LISTENING_SETS:
        (listening_dir / f"{spec['slug']}.wav").write_bytes(make_wav(4000))
    call_command("seed_listening_content", verbosity=0)
    return tmp_path


@pytest.fixture
def apt() -> MediaAsset:
    return MediaAsset.objects.get(content_version__item__slug=APT_SLUG)


def make_rendition(
    asset: MediaAsset,
    provider: str,
    *,
    clip: bytes | None = None,
    status: str = MediaStatus.READY,
) -> AudioRendition:
    clip = clip if clip is not None else make_wav(3500, sample=b"\x02\x00")
    storage_key = f"listening_renditions/{provider}/{asset.id}.wav"
    path = private_media_path(storage_key)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(clip)
    return AudioRendition.objects.create(
        canonical_asset=asset,
        provider=provider,
        storage_key=storage_key,
        mime_type="audio/wav",
        byte_size=len(clip),
        duration_ms=3500,
        checksum_sha256=file_checksum(path),
        model_name="test-model",
        provenance="Test rendition provenance.",
        status=status,
    )


def make_learner(preferred: str) -> User:
    user = User.objects.create_user(identifier=f"learner-{preferred}", password="pw")
    LearnerProfile.objects.create(user=user, preferred_audio_provider=preferred)
    return user


def start_session(api_client, slug=APT_SLUG, mode="practice"):
    return api_client.post(
        SESSIONS_URL,
        {"content_slug": slug, "mode": mode, "time_limit_seconds": 900},
        format="json",
    )


# ── select_audio_source: explicit preferences ────────────────────────────────
def test_explicit_openai_selects_ready_rendition(isolated_listening, apt):
    rendition = make_rendition(apt, "openai")

    source = select_audio_source(apt, preferred=PreferredAudioProvider.OPENAI)

    assert source.provider == "openai"
    assert source.rendition_id == rendition.id
    assert source.storage_key == rendition.storage_key
    assert source.byte_size == rendition.byte_size
    assert source.checksum_sha256 == rendition.checksum_sha256
    assert source.canonical_asset == apt


def test_explicit_azure_selects_ready_rendition(isolated_listening, apt):
    make_rendition(apt, "openai")
    azure = make_rendition(apt, "azure")

    source = select_audio_source(apt, preferred=PreferredAudioProvider.AZURE)

    assert source.provider == "azure"
    assert source.rendition_id == azure.id


def test_explicit_local_selects_canonical(isolated_listening, apt):
    make_rendition(apt, "openai")

    source = select_audio_source(apt, preferred=PreferredAudioProvider.LOCAL)

    assert source.provider == "local"
    assert source.rendition_id is None
    assert source.storage_key == apt.storage_key
    assert source.byte_size == apt.byte_size


# ── select_audio_source: automatic ordering ──────────────────────────────────
def test_automatic_follows_configured_provider_order(isolated_listening, apt):
    # With both remote renditions present, automatic honours the configured
    # order (openai, azure, local) and takes the first: openai.
    make_rendition(apt, "openai")
    make_rendition(apt, "azure")

    assert select_audio_source(apt).provider == "openai"


def test_automatic_skips_missing_first_provider(isolated_listening, apt):
    # Only azure exists; automatic skips the missing openai and lands on azure.
    make_rendition(apt, "azure")

    assert select_audio_source(apt).provider == "azure"


def test_automatic_falls_back_to_local_when_no_renditions(isolated_listening, apt):
    assert select_audio_source(apt).provider == "local"


# ── select_audio_source: fall-through on missing / invalid preferred ──────────
def test_missing_preferred_falls_through_to_order(isolated_listening, apt):
    # Learner prefers openai, but no openai rendition exists. Selection falls
    # through the configured order to azure.
    make_rendition(apt, "azure")

    source = select_audio_source(apt, preferred=PreferredAudioProvider.OPENAI)

    assert source.provider == "azure"


def test_invalid_preferred_rendition_falls_through(isolated_listening, apt):
    # A preferred rendition whose file is corrupted (checksum mismatch) is not
    # trusted; selection falls through rather than serving tampered bytes.
    openai = make_rendition(apt, "openai")
    make_rendition(apt, "azure")
    private_media_path(openai.storage_key).write_bytes(make_wav(3500, sample=b"\xff\x7f"))

    source = select_audio_source(apt, preferred=PreferredAudioProvider.OPENAI)

    assert source.provider == "azure"


def test_all_invalid_falls_back_to_local(isolated_listening, apt):
    openai = make_rendition(apt, "openai")
    private_media_path(openai.storage_key).unlink()

    source = select_audio_source(apt, preferred=PreferredAudioProvider.OPENAI)

    assert source.provider == "local"


def test_non_ready_rendition_is_ignored(isolated_listening, apt):
    make_rendition(apt, "openai", status=MediaStatus.PENDING)

    assert select_audio_source(apt, preferred=PreferredAudioProvider.OPENAI).provider == (
        "local"
    )


# ── select_audio_source: guest and authenticated learner ─────────────────────
def test_guest_uses_automatic_order(isolated_listening, apt):
    make_rendition(apt, "openai")

    # No user (guest) and no explicit preference: automatic order picks openai.
    assert select_audio_source(apt, user=None).provider == "openai"


def test_authenticated_profile_preference_is_used(isolated_listening, apt):
    make_rendition(apt, "openai")
    make_rendition(apt, "azure")
    learner = make_learner(PreferredAudioProvider.AZURE)

    source = select_audio_source(apt, user=learner)

    assert source.provider == "azure"


def test_authenticated_automatic_profile_uses_order(isolated_listening, apt):
    make_rendition(apt, "azure")
    learner = make_learner(PreferredAudioProvider.AUTOMATIC)

    # An "automatic" stored preference behaves like a guest: configured order.
    assert select_audio_source(apt, user=learner).provider == "azure"


def test_no_playable_source_raises(isolated_listening, apt):
    apt.status = MediaStatus.PENDING
    apt.save(update_fields=["status"])

    with pytest.raises(MediaUnavailable):
        select_audio_source(apt, preferred=PreferredAudioProvider.LOCAL)


# ── grant_audio_access: token binding + shared one-play limit ─────────────────
def test_grant_binds_selected_provider_into_token(isolated_listening, apt, api_client):
    make_rendition(apt, "openai")
    started = start_session(api_client)
    session = _session_from(started)
    learner = make_learner(PreferredAudioProvider.OPENAI)

    access = grant_audio_access(session=session, asset=apt, user=learner)

    assert access.selected_provider == "openai"
    assert access.url.startswith(f"/api/v1/media/audio/{apt.id}/stream/?token=")
    payload = _payload(access.url)
    assert payload["scope"] == "session"
    assert payload["asset_id"] == str(apt.id)
    assert payload["provider"] == "openai"
    assert payload["rendition_id"] == str(
        AudioRendition.objects.get(canonical_asset=apt, provider="openai").id
    )


def test_local_grant_binds_null_rendition(isolated_listening, apt, api_client):
    started = start_session(api_client)
    session = _session_from(started)

    access = grant_audio_access(session=session, asset=apt)

    assert access.selected_provider == "local"
    assert _payload(access.url)["rendition_id"] is None


def test_one_play_limit_is_shared_across_providers(isolated_listening, apt, api_client):
    make_rendition(apt, "openai")
    started = start_session(api_client)
    session = _session_from(started)

    first = grant_audio_access(
        session=session, asset=apt, user=make_learner(PreferredAudioProvider.OPENAI)
    )
    assert first.plays_remaining == 0

    # The one-play grant is keyed on the canonical asset, so switching the
    # preferred provider cannot buy a second playback.
    with pytest.raises(PlaybackLimitReached):
        grant_audio_access(
            session=session, asset=apt, user=make_learner(PreferredAudioProvider.LOCAL)
        )
    assert MediaPlaybackGrant.objects.get(session=session, asset=apt).grants_issued == 1


# ── verify_stream_token: exact binding, tamper, cross-session ─────────────────
def test_verify_returns_exact_rendition_source(isolated_listening, apt, api_client):
    rendition = make_rendition(apt, "openai")
    started = start_session(api_client)
    session = _session_from(started)
    access = grant_audio_access(
        session=session, asset=apt, user=make_learner(PreferredAudioProvider.OPENAI)
    )

    source = verify_stream_token(asset_id=apt.id, token=_token(access.url))

    assert source.provider == "openai"
    assert source.rendition_id == rendition.id
    assert source.storage_key == rendition.storage_key
    assert source.mime_type == rendition.mime_type


def test_verify_rejects_tampered_token(isolated_listening, apt, api_client):
    make_rendition(apt, "openai")
    started = start_session(api_client)
    access = grant_audio_access(
        session=_session_from(started),
        asset=apt,
        user=make_learner(PreferredAudioProvider.OPENAI),
    )

    with pytest.raises(MediaAccessError):
        verify_stream_token(asset_id=apt.id, token=_token(access.url) + "x")


def test_verify_fails_when_bound_source_file_tampered(isolated_listening, apt, api_client):
    rendition = make_rendition(apt, "openai")
    started = start_session(api_client)
    access = grant_audio_access(
        session=_session_from(started),
        asset=apt,
        user=make_learner(PreferredAudioProvider.OPENAI),
    )

    # Corrupt the exact rendition the token is bound to; no fallback is allowed.
    private_media_path(rendition.storage_key).write_bytes(make_wav(3500, sample=b"\x09\x00"))

    with pytest.raises(MediaUnavailable):
        verify_stream_token(asset_id=apt.id, token=_token(access.url))


def test_verify_fails_when_bound_rendition_missing_no_fallback(
    isolated_listening, apt, api_client
):
    make_rendition(apt, "openai")
    started = start_session(api_client)
    access = grant_audio_access(
        session=_session_from(started),
        asset=apt,
        user=make_learner(PreferredAudioProvider.OPENAI),
    )

    # Delete the bound rendition entirely. Even though a valid local canonical
    # exists, an openai-bound token must not silently fall back to it.
    AudioRendition.objects.filter(canonical_asset=apt, provider="openai").delete()

    with pytest.raises(MediaUnavailable):
        verify_stream_token(asset_id=apt.id, token=_token(access.url))


def test_verify_rejects_non_session_scope(isolated_listening, apt, api_client):
    started = start_session(api_client)
    session = _session_from(started)
    grant_audio_access(session=session, asset=apt)
    # A token minted with any scope other than "session" is refused for now.
    token = signing.dumps(
        {
            "scope": "preview",
            "asset_id": str(apt.id),
            "session_id": str(session.id),
            "provider": "local",
            "rendition_id": None,
        },
        salt=TOKEN_SALT,
        compress=True,
    )

    with pytest.raises(MediaAccessError):
        verify_stream_token(asset_id=apt.id, token=token)


def test_verify_rejects_token_without_matching_grant(isolated_listening, apt, api_client):
    started = start_session(api_client)
    session = _session_from(started)
    access = grant_audio_access(session=session, asset=apt)

    # Remove the grant to simulate a token bound to a session that never
    # obtained (or has lost) playback rights for this asset.
    MediaPlaybackGrant.objects.filter(session=session, asset=apt).delete()

    with pytest.raises(MediaAccessError):
        verify_stream_token(asset_id=apt.id, token=_token(access.url))


# ── helpers ──────────────────────────────────────────────────────────────────
def _session_from(started):
    from apps.assessments.models import AssessmentSession

    return AssessmentSession.objects.get(pk=started.json()["id"])


def _token(url: str) -> str:
    return url.split("token=", 1)[1]


def _payload(url: str) -> dict:
    return signing.loads(_token(url), salt=TOKEN_SALT, max_age=600)
