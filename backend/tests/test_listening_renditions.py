"""Per-provider Listening audio renditions: generation, safety, and isolation."""
from __future__ import annotations

import io
import wave
from types import SimpleNamespace

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.content.listening_seed_data import LISTENING_SETS as LISTENING_SETS_BASE
from apps.content.listening_seed_data_v2 import LISTENING_SETS as LISTENING_SETS_V2
from apps.content.listening_seed_data_v3 import LISTENING_SETS as LISTENING_SETS_V3
from apps.media_assets.audio_synthesis import (
    AzureVoiceProvider,
    OpenAIVoiceProvider,
)
from apps.media_assets.management.commands.generate_listening_renditions import (
    Command as RenditionCommand,
)
from apps.media_assets.models import AudioRendition, MediaAsset, MediaStatus

LISTENING_SETS = LISTENING_SETS_BASE + LISTENING_SETS_V2 + LISTENING_SETS_V3
from apps.media_assets.services import file_checksum, private_media_path

pytestmark = pytest.mark.django_db

FAKE_KEY = "sk-should-never-appear-anywhere"


def gen(*args):
    call_command("generate_listening_renditions", *args, verbosity=0)


def make_wav(ms: int, *, frame_rate: int = 16000, channels: int = 1, width: int = 2) -> bytes:
    frames = int(frame_rate * ms / 1000)
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as writer:
        writer.setnchannels(channels)
        writer.setsampwidth(width)
        writer.setframerate(frame_rate)
        writer.writeframes(b"\x01\x00" * frames * channels)
    return buffer.getvalue()


class FakeSpeech:
    def __init__(self, clip: bytes):
        self.clip = clip
        self.calls: list[dict] = []

    def create(self, *, model, voice, input, response_format):
        self.calls.append(
            {"model": model, "voice": voice, "input": input, "format": response_format}
        )
        return SimpleNamespace(read=lambda: self.clip)


def fake_openai_client(clip: bytes):
    return SimpleNamespace(audio=SimpleNamespace(speech=FakeSpeech(clip)))


class FakeAzureTransport:
    def __init__(self, clip: bytes):
        self.clip = clip
        self.calls: list[dict] = []

    def __call__(self, url, ssml, output_format):
        self.calls.append({"url": url, "ssml": ssml, "format": output_format})
        return self.clip


@pytest.fixture
def isolated_listening(tmp_path, settings):
    """Seed Listening content into an isolated private-media root."""
    settings.PRIVATE_MEDIA_ROOT = tmp_path
    listening_dir = tmp_path / "listening"
    listening_dir.mkdir()
    for spec in LISTENING_SETS:
        (listening_dir / f"{spec['slug']}.wav").write_bytes(make_wav(4000))
    call_command("seed_listening_content", verbosity=0)
    return tmp_path


def _patch_provider(monkeypatch, *, openai=None, azure=None):
    """Make the command build the given fake providers for each request."""

    def builder(name):
        if name == "openai":
            if callable(openai):
                return openai()
            return openai if openai is not None else OpenAIVoiceProvider(voices=["alloy", "onyx"])
        if name == "azure":
            if callable(azure):
                return azure()
            return azure if azure is not None else AzureVoiceProvider(voices=["a", "b"])
        raise ValueError(name)

    monkeypatch.setattr(
        "apps.media_assets.management.commands.generate_listening_renditions.build_rendition_provider",
        builder,
    )


def _openai_provider(clip: bytes, **kwargs):
    return OpenAIVoiceProvider(client=fake_openai_client(clip), voices=["alloy", "onyx"], **kwargs)


# ── Generation / scoping / canonical preservation ────────────────────────────
def test_command_generates_scoped_rendition_and_preserves_canonical(
    isolated_listening, settings, monkeypatch
):
    settings.OPENAI_API_KEY = FAKE_KEY
    _patch_provider(monkeypatch, openai=_openai_provider(make_wav(3500)))

    apt = MediaAsset.objects.get(content_version__item__slug="apartment-heating-plan")
    canonical_path = private_media_path(apt.storage_key)
    before = canonical_path.read_bytes()
    before_checksum = apt.checksum_sha256

    gen("--provider", "openai", "--slug", "apartment-heating-plan", "--force")

    rendition = AudioRendition.objects.get(canonical_asset=apt, provider="openai")
    assert AudioRendition.objects.count() == 1  # scope respected
    assert rendition.status == MediaStatus.READY
    assert rendition.mime_type == "audio/wav"
    assert rendition.storage_key == f"listening_renditions/openai/{apt.id}.wav"
    rendition_path = private_media_path(rendition.storage_key)
    assert rendition_path.is_file()
    assert rendition.checksum_sha256 == file_checksum(rendition_path)
    assert rendition.byte_size == rendition_path.stat().st_size
    assert "OpenAI" in rendition.provenance and rendition.model_name
    assert FAKE_KEY not in rendition.provenance
    assert FAKE_KEY not in rendition.voice_label

    # The canonical asset and its file are never touched.
    assert canonical_path.read_bytes() == before
    apt.refresh_from_db()
    assert apt.checksum_sha256 == before_checksum
    assert rendition.storage_key != apt.storage_key


def test_command_accepts_comma_separated_and_repeatable_providers(
    isolated_listening, settings, monkeypatch
):
    settings.OPENAI_API_KEY = FAKE_KEY
    settings.AZURE_SPEECH_KEY = FAKE_KEY
    settings.AZURE_SPEECH_REGION = "canadacentral"
    _patch_provider(
        monkeypatch,
        openai=_openai_provider(make_wav(3500)),
        azure=AzureVoiceProvider(
            transport=FakeAzureTransport(make_wav(3500)), voices=["a", "b"]
        ),
    )

    gen("--provider", "openai,azure", "--slug", "apartment-heating-plan", "--force")
    apt = MediaAsset.objects.get(content_version__item__slug="apartment-heating-plan")
    assert set(
        AudioRendition.objects.filter(canonical_asset=apt).values_list(
            "provider", flat=True
        )
    ) == {"openai", "azure"}

    gen(
        "--provider", "openai", "--provider", "azure",
        "--slug", "pottery-class-change", "--force",
    )
    other = MediaAsset.objects.get(content_version__item__slug="pottery-class-change")
    assert set(
        AudioRendition.objects.filter(canonical_asset=other).values_list(
            "provider", flat=True
        )
    ) == {"openai", "azure"}


# ── Missing credentials ──────────────────────────────────────────────────────
def test_command_missing_credentials_mutates_nothing(isolated_listening, settings):
    settings.OPENAI_API_KEY = ""

    gen("--provider", "openai", "--force")

    assert AudioRendition.objects.count() == 0
    assert not (settings.PRIVATE_MEDIA_ROOT / "listening_renditions").exists()


# ── Dry run ──────────────────────────────────────────────────────────────────
def test_command_dry_run_calls_no_provider_and_writes_nothing(
    isolated_listening, settings, monkeypatch
):
    settings.OPENAI_API_KEY = FAKE_KEY
    speech = FakeSpeech(make_wav(3500))
    _patch_provider(
        monkeypatch,
        openai=OpenAIVoiceProvider(
            client=SimpleNamespace(audio=SimpleNamespace(speech=speech)),
            voices=["alloy", "onyx"],
        ),
    )

    gen("--provider", "openai", "--force", "--dry-run")

    assert speech.calls == []  # no provider was called
    assert AudioRendition.objects.count() == 0
    assert not (settings.PRIVATE_MEDIA_ROOT / "listening_renditions").exists()


# ── Force / idempotence ──────────────────────────────────────────────────────
def test_command_skips_valid_and_is_idempotent(isolated_listening, settings, monkeypatch):
    settings.OPENAI_API_KEY = FAKE_KEY
    _patch_provider(monkeypatch, openai=_openai_provider(make_wav(3500)))

    apt = MediaAsset.objects.get(content_version__item__slug="apartment-heating-plan")

    gen("--provider", "openai", "--slug", "apartment-heating-plan")
    rendition = AudioRendition.objects.get(canonical_asset=apt, provider="openai")
    first_checksum = rendition.checksum_sha256

    # A second run without --force skips the already-valid rendition.
    gen("--provider", "openai", "--slug", "apartment-heating-plan")
    assert AudioRendition.objects.count() == 1

    # --force resynthesizes, but the identical checksum means no rewrite.
    gen("--provider", "openai", "--slug", "apartment-heating-plan", "--force")
    rendition.refresh_from_db()
    assert AudioRendition.objects.count() == 1
    assert rendition.checksum_sha256 == first_checksum


def test_command_force_regenerates_when_bytes_change(
    isolated_listening, settings, monkeypatch
):
    settings.OPENAI_API_KEY = FAKE_KEY
    clips = iter([make_wav(3500), make_wav(4000)])
    _patch_provider(monkeypatch, openai=lambda: _openai_provider(next(clips)))

    apt = MediaAsset.objects.get(content_version__item__slug="apartment-heating-plan")

    gen("--provider", "openai", "--slug", "apartment-heating-plan", "--force")
    rendition = AudioRendition.objects.get(canonical_asset=apt, provider="openai")
    first_size = rendition.byte_size
    first_checksum = rendition.checksum_sha256

    gen("--provider", "openai", "--slug", "apartment-heating-plan", "--force")
    rendition.refresh_from_db()
    assert AudioRendition.objects.count() == 1
    assert rendition.checksum_sha256 != first_checksum
    assert rendition.byte_size != first_size


# ── Rollback / batch isolation ───────────────────────────────────────────────
def test_command_isolates_single_asset_write_failure(
    isolated_listening, settings, monkeypatch
):
    settings.OPENAI_API_KEY = FAKE_KEY
    _patch_provider(monkeypatch, openai=_openai_provider(make_wav(3500)))

    apt = MediaAsset.objects.get(content_version__item__slug="apartment-heating-plan")
    apt_rendition_path = (
        settings.PRIVATE_MEDIA_ROOT / "listening_renditions" / "openai" / f"{apt.id}.wav"
    )

    original_atomic_write = RenditionCommand._atomic_write

    def failing_write(target, data):
        if target.name == f"{apt.id}.wav":
            raise OSError("simulated disk full")
        return original_atomic_write(target, data)

    monkeypatch.setattr(RenditionCommand, "_atomic_write", staticmethod(failing_write))

    # One asset fails to write; the command records it and keeps going rather
    # than aborting the whole batch.
    with pytest.raises(CommandError):
        gen("--provider", "openai", "--force")

    assert not apt_rendition_path.exists()
    assert not AudioRendition.objects.filter(
        canonical_asset=apt, provider="openai"
    ).exists()
    other = MediaAsset.objects.get(content_version__item__slug="pottery-class-change")
    assert AudioRendition.objects.filter(
        canonical_asset=other, provider="openai"
    ).exists()  # the rest of the batch still ran


def test_command_rolls_back_file_when_db_write_fails(
    isolated_listening, settings, monkeypatch
):
    settings.OPENAI_API_KEY = FAKE_KEY
    _patch_provider(monkeypatch, openai=_openai_provider(make_wav(3500)))

    apt = MediaAsset.objects.get(content_version__item__slug="apartment-heating-plan")
    rendition_path = (
        settings.PRIVATE_MEDIA_ROOT / "listening_renditions" / "openai" / f"{apt.id}.wav"
    )

    def boom(self, *args, **kwargs):
        raise RuntimeError("simulated database failure")

    monkeypatch.setattr(AudioRendition, "save", boom)

    with pytest.raises(CommandError):
        gen("--provider", "openai", "--slug", "apartment-heating-plan", "--force")

    # The freshly written file was rolled back and no row remains.
    assert not rendition_path.exists()
    assert AudioRendition.objects.count() == 0
