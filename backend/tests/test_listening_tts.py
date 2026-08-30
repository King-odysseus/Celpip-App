"""Provider-ordered Listening audio synthesis, regeneration, and safety."""
from __future__ import annotations

import io
import wave
from types import SimpleNamespace

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.content.listening_seed_data import LISTENING_SETS
from apps.media_assets.audio_synthesis import (
    AzureVoiceProvider,
    LocalRetainProvider,
    OpenAIVoiceProvider,
    SynthesisError,
    concatenate_wav,
    parse_dialogue,
    synthesize_listening_audio,
    validate_wav_bytes,
)
from apps.media_assets.management.commands.regenerate_listening_audio import (
    Command as RegenCommand,
)
from apps.media_assets.models import MediaAsset, MediaStatus
from apps.media_assets.services import file_checksum, private_media_path

pytestmark = pytest.mark.django_db

FAKE_KEY = "sk-should-never-appear-anywhere"


def regen(*args):
    call_command("regenerate_listening_audio", *args, verbosity=0)


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


# ── Pure helpers ─────────────────────────────────────────────────────────────
def test_parse_dialogue_alternates_two_voices_and_merges_monologue():
    two_speaker = "Nadia: Hello there.\nColin: Hi Nadia.\nNadia: How are you?"
    chunks = parse_dialogue(two_speaker, "alloy", "onyx")
    assert [voice for voice, _ in chunks] == ["alloy", "onyx", "alloy"]

    # Ann→alloy, Bob→onyx, Cy→alloy (third speaker cycles back). Cy then Ann are
    # both alloy and adjacent, so they merge into a single alloy chunk.
    third = "Ann: One.\nBob: Two.\nCy: Three.\nAnn: Four."
    chunks = parse_dialogue(third, "alloy", "onyx")
    assert [voice for voice, _ in chunks] == ["alloy", "onyx", "alloy"]
    assert chunks[-1] == ("alloy", "Three. Four.")

    monologue = "Speaker: First sentence.\nSecond continues.\nThird continues."
    chunks = parse_dialogue(monologue, "alloy", "onyx")
    assert len(chunks) == 1
    assert chunks[0] == ("alloy", "First sentence. Second continues. Third continues.")


def test_validate_wav_rejects_corrupt_and_too_short():
    assert validate_wav_bytes(make_wav(4000)).duration_ms >= 3000
    with pytest.raises(SynthesisError):
        validate_wav_bytes(b"not a wav at all")
    with pytest.raises(SynthesisError, match="too short"):
        validate_wav_bytes(make_wav(500))
    with pytest.raises(SynthesisError):
        validate_wav_bytes(b"")


def test_concatenate_preserves_frames_and_rejects_mismatch():
    joined = concatenate_wav([make_wav(1000), make_wav(2000)])
    with wave.open(io.BytesIO(joined), "rb") as reader:
        assert round(reader.getnframes() / reader.getframerate() * 1000) == 3000

    with pytest.raises(SynthesisError, match="incompatible"):
        concatenate_wav([make_wav(1000), make_wav(1000, frame_rate=8000)])


# ── Provider precedence and fall-through (unit) ──────────────────────────────
def test_precedence_prefers_first_available_provider(settings):
    settings.OPENAI_API_KEY = FAKE_KEY
    clip = make_wav(3500)
    openai = OpenAIVoiceProvider(client=fake_openai_client(clip), voices=["alloy", "onyx"])
    azure = AzureVoiceProvider(transport=FakeAzureTransport(clip), voices=["a", "b"])

    run = synthesize_listening_audio("X: hello there friend", [openai, azure])
    assert run.result.provider == "openai"
    assert [a.name for a in run.attempts] == ["openai"]
    assert run.attempts[0].outcome == "used"


def test_missing_credentials_skip_to_local(settings):
    settings.OPENAI_API_KEY = ""
    settings.AZURE_SPEECH_KEY = ""
    settings.AZURE_SPEECH_REGION = ""
    existing = make_wav(4000)
    providers = [
        OpenAIVoiceProvider(voices=["alloy", "onyx"]),
        AzureVoiceProvider(voices=["a", "b"]),
        LocalRetainProvider(existing_bytes=existing, voice_label="local voice"),
    ]
    run = synthesize_listening_audio("X: hi there", providers)
    assert run.result.provider == "local"
    assert [a.outcome for a in run.attempts] == ["skipped", "skipped", "used"]


def test_openai_failure_falls_through_to_azure(settings):
    settings.OPENAI_API_KEY = FAKE_KEY
    clip = make_wav(3500)

    class Boom:
        def create(self, **kwargs):
            raise RuntimeError("upstream 500 with secret body")

    openai = OpenAIVoiceProvider(
        client=SimpleNamespace(audio=SimpleNamespace(speech=Boom())),
        voices=["alloy", "onyx"],
    )
    transport = FakeAzureTransport(clip)
    azure = AzureVoiceProvider(
        transport=transport, voices=["en-CA-ClaraNeural", "en-CA-LiamNeural"]
    )

    run = synthesize_listening_audio("Nadia: one two.\nColin: three four.", [openai, azure])
    assert run.result.provider == "azure"
    assert run.attempts[0].outcome == "error"
    assert "secret" not in run.attempts[0].detail  # opaque message only
    assert len(transport.calls) == 2  # two speakers → two Azure requests


def test_invalid_provider_output_is_discarded(settings):
    settings.OPENAI_API_KEY = FAKE_KEY
    short = make_wav(200)  # below the usable floor
    openai = OpenAIVoiceProvider(client=fake_openai_client(short), voices=["alloy", "onyx"])
    good = AzureVoiceProvider(transport=FakeAzureTransport(make_wav(3500)), voices=["a", "b"])

    run = synthesize_listening_audio("X: hello", [openai, good])
    assert run.attempts[0].outcome == "invalid"
    assert run.result.provider == "azure"


def test_all_fail_returns_no_result():
    class Boom:
        def create(self, **kwargs):
            raise RuntimeError("no")

    openai = OpenAIVoiceProvider(
        client=SimpleNamespace(audio=SimpleNamespace(speech=Boom())),
        voices=["alloy", "onyx"],
    )
    local = LocalRetainProvider(existing_bytes=None)  # nothing to retain
    run = synthesize_listening_audio("X: hi", [openai, local])
    assert run.result is None
    assert run.attempts[-1].outcome == "skipped"


# ── Command integration ──────────────────────────────────────────────────────
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


def _patch_builder(monkeypatch, *, openai=None, azure=None, clip=None):
    """Make the command build the given fake providers for each asset."""

    def builder(order, *, existing_bytes, existing_voice_label=""):
        made = []
        for name in order:
            if name == "openai":
                made.append(
                    openai()
                    if callable(openai)
                    else (openai or OpenAIVoiceProvider(voices=["alloy", "onyx"]))
                )
            elif name == "azure":
                made.append(
                    azure()
                    if callable(azure)
                    else (azure or AzureVoiceProvider(voices=["a", "b"]))
                )
            elif name == "local":
                made.append(
                    LocalRetainProvider(
                        existing_bytes=existing_bytes, voice_label=existing_voice_label
                    )
                )
        return made

    monkeypatch.setattr(
        "apps.media_assets.management.commands.regenerate_listening_audio.build_default_providers",
        builder,
    )


def test_command_regenerates_and_captures_safe_metadata(isolated_listening, settings, monkeypatch):
    settings.OPENAI_API_KEY = FAKE_KEY
    clip = make_wav(3500)
    fake = fake_openai_client(clip)
    _patch_builder(
        monkeypatch,
        openai=OpenAIVoiceProvider(client=fake, model="gpt-4o-mini-tts", voices=["alloy", "onyx"]),
    )

    regen("--slug", "apartment-heating-plan", "--force")

    asset = MediaAsset.objects.get(content_version__item__slug="apartment-heating-plan")
    path = private_media_path(asset.storage_key)
    assert asset.status == MediaStatus.READY
    assert asset.mime_type == "audio/wav"
    assert asset.byte_size == path.stat().st_size
    assert asset.checksum_sha256 == file_checksum(path)
    assert asset.duration_ms > 0
    assert asset.voice_label == "alloy, onyx"
    assert "OpenAI" in asset.provenance and "gpt-4o-mini-tts" in asset.provenance
    # Secrets must never leak into metadata or provenance.
    assert FAKE_KEY not in asset.provenance
    assert FAKE_KEY not in asset.voice_label


def test_command_dialogue_alternates_two_openai_voices(isolated_listening, settings, monkeypatch):
    settings.OPENAI_API_KEY = FAKE_KEY
    speech = FakeSpeech(make_wav(600))
    client = SimpleNamespace(audio=SimpleNamespace(speech=speech))
    _patch_builder(
        monkeypatch,
        openai=OpenAIVoiceProvider(client=client, voices=["alloy", "onyx"]),
    )

    regen("--slug", "apartment-heating-plan", "--force")

    voices_used = {call["voice"] for call in speech.calls}
    assert voices_used == {"alloy", "onyx"}
    assert all(call["format"] == "wav" for call in speech.calls)


def test_command_openai_failure_falls_to_azure(isolated_listening, settings, monkeypatch):
    settings.OPENAI_API_KEY = FAKE_KEY

    class Boom:
        def create(self, **kwargs):
            raise RuntimeError("secret 500")

    openai = OpenAIVoiceProvider(
        client=SimpleNamespace(audio=SimpleNamespace(speech=Boom())), voices=["alloy", "onyx"]
    )
    azure = AzureVoiceProvider(
        transport=FakeAzureTransport(make_wav(3500)),
        voices=["en-CA-ClaraNeural", "en-CA-LiamNeural"],
    )
    _patch_builder(monkeypatch, openai=openai, azure=azure)

    regen("--slug", "mobile-health-clinic-news", "--force")

    asset = MediaAsset.objects.get(content_version__item__slug="mobile-health-clinic-news")
    assert "Azure" in asset.provenance
    assert asset.voice_label == "en-CA-ClaraNeural, en-CA-LiamNeural"


def test_command_both_remote_fail_retains_existing_file(isolated_listening, settings, monkeypatch):
    settings.OPENAI_API_KEY = ""
    settings.AZURE_SPEECH_KEY = ""
    settings.AZURE_SPEECH_REGION = ""
    asset = MediaAsset.objects.get(content_version__item__slug="apartment-heating-plan")
    path = private_media_path(asset.storage_key)
    before_bytes = path.read_bytes()
    before_checksum = asset.checksum_sha256

    _patch_builder(monkeypatch)  # openai/azure unavailable, local retains

    regen("--slug", "apartment-heating-plan", "--force")

    asset.refresh_from_db()
    assert path.read_bytes() == before_bytes  # file untouched
    assert asset.checksum_sha256 == before_checksum


def test_command_never_clobbers_when_all_fail_and_no_valid_existing(
    isolated_listening, settings, monkeypatch
):
    settings.OPENAI_API_KEY = FAKE_KEY
    asset = MediaAsset.objects.get(content_version__item__slug="apartment-heating-plan")
    path = private_media_path(asset.storage_key)
    corrupt = b"RIFFcorrupt-not-a-wav"
    path.write_bytes(corrupt)  # existing on-disk file is invalid

    class Boom:
        def create(self, **kwargs):
            raise RuntimeError("no")

    openai = OpenAIVoiceProvider(
        client=SimpleNamespace(audio=SimpleNamespace(speech=Boom())), voices=["alloy", "onyx"]
    )
    _patch_builder(monkeypatch, openai=openai)

    with pytest.raises(CommandError):
        regen("--slug", "apartment-heating-plan", "--force")
    assert path.read_bytes() == corrupt  # invalid file preserved, not destroyed


def test_command_isolates_single_asset_write_failure(isolated_listening, settings, monkeypatch):
    settings.OPENAI_API_KEY = FAKE_KEY
    fake = fake_openai_client(make_wav(3500))
    _patch_builder(
        monkeypatch,
        openai=OpenAIVoiceProvider(client=fake, voices=["alloy", "onyx"]),
    )

    apt_asset = MediaAsset.objects.get(content_version__item__slug="apartment-heating-plan")
    apt_path = private_media_path(apt_asset.storage_key)
    before = apt_path.read_bytes()

    original_atomic_write = RegenCommand._atomic_write

    def failing_write(target, data):
        if target.name == "apartment-heating-plan.wav":
            raise OSError("simulated disk full")
        return original_atomic_write(target, data)

    monkeypatch.setattr(RegenCommand, "_atomic_write", staticmethod(failing_write))

    # One asset fails to write; the command records it and keeps going rather
    # than aborting the whole batch.
    with pytest.raises(CommandError):
        regen("--force")

    assert apt_path.read_bytes() == before  # failed asset left untouched
    other = MediaAsset.objects.get(content_version__item__slug="pottery-class-change")
    assert other.voice_label == "alloy, onyx"  # the rest of the batch still ran


def test_command_dry_run_calls_no_provider_and_writes_nothing(
    isolated_listening, settings, monkeypatch
):
    settings.OPENAI_API_KEY = FAKE_KEY
    speech = FakeSpeech(make_wav(3500))
    client = SimpleNamespace(audio=SimpleNamespace(speech=speech))
    asset = MediaAsset.objects.get(content_version__item__slug="apartment-heating-plan")
    path = private_media_path(asset.storage_key)
    before = path.read_bytes()
    _patch_builder(monkeypatch, openai=OpenAIVoiceProvider(client=client, voices=["alloy", "onyx"]))

    regen("--slug", "apartment-heating-plan", "--force", "--dry-run")

    assert speech.calls == []  # no provider was called
    assert path.read_bytes() == before  # nothing written


def test_command_default_skips_valid_and_is_scoped_and_idempotent(
    isolated_listening, settings, monkeypatch
):
    settings.OPENAI_API_KEY = FAKE_KEY
    speech = FakeSpeech(make_wav(3500))
    client = SimpleNamespace(audio=SimpleNamespace(speech=speech))
    _patch_builder(monkeypatch, openai=OpenAIVoiceProvider(client=client, voices=["alloy", "onyx"]))

    # Without --force every seeded asset is already valid, so nothing is synthesized.
    regen()
    assert speech.calls == []

    # Scope + force regenerates exactly one asset; a second run is idempotent
    # because the deterministic clip yields an identical checksum.
    regen("--slug", "pottery-class-change", "--force")
    first = MediaAsset.objects.get(content_version__item__slug="pottery-class-change")
    first_checksum = first.checksum_sha256
    others_touched = MediaAsset.objects.exclude(
        content_version__item__slug="pottery-class-change"
    ).values_list("voice_label", flat=True)
    assert all(label != "alloy, onyx" for label in others_touched)  # scope respected

    regen("--slug", "pottery-class-change", "--force")
    first.refresh_from_db()
    assert first.checksum_sha256 == first_checksum  # idempotent


def test_azure_provider_never_places_key_in_request_url(settings):
    settings.AZURE_SPEECH_KEY = FAKE_KEY
    settings.AZURE_SPEECH_REGION = "canadacentral"
    transport = FakeAzureTransport(make_wav(3500))
    azure = AzureVoiceProvider(transport=transport, key=FAKE_KEY, region="canadacentral")
    azure.synthesize("X: hello there world")
    for call in transport.calls:
        assert FAKE_KEY not in call["url"]
        assert FAKE_KEY not in call["ssml"]


def test_azure_ssml_escapes_voice_and_text():
    azure = AzureVoiceProvider(voices=["en-CA-ClaraNeural", "en-CA-LiamNeural"])
    ssml = azure._ssml('en-CA-Test"Neural', "A < B & C > D")
    assert '<voice name="en-CA-Test&quot;Neural">' in ssml
    assert "<prosody rate=\"-3%\">A &lt; B &amp; C &gt; D</prosody>" in ssml
