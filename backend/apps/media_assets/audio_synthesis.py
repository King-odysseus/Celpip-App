"""Provider-ordered Listening audio synthesis.

Stored CELPIP-General Listening audio is generated once and reused. This module
turns a reviewed transcript into a validated WAV using an ordered list of speech
providers. The order (default ``openai,azure,local``) is independent of
``AI_PROVIDER`` so general AI evaluation may run on a fake provider while audio
is still produced by a live speech vendor.

Guarantees:

* Every candidate is strictly validated as RIFF PCM WAV *before* it is used, so
  invalid, corrupt, or too-short output is discarded and the next provider is
  tried.
* No provider ever writes to the stored file. This module only returns bytes;
  the management command performs the atomic, no-clobber replacement. If every
  provider fails, the caller keeps the existing recording untouched.
* Secrets (API keys) never enter logs, results, provenance, or exceptions.
"""
from __future__ import annotations

import io
import re
import wave
from dataclasses import dataclass, field
from datetime import date
from typing import Protocol

from django.conf import settings

# Bounds mirror the MediaAsset model validators (duration_ms / byte_size).
MIN_DURATION_MS = 1_000
MAX_DURATION_MS = 10 * 60 * 1_000
MAX_BYTE_SIZE = 20 * 1024 * 1024
# A generated Listening recording shorter than this almost certainly means the
# provider returned a truncated or silent clip; treat it as invalid output.
MIN_GENERATED_DURATION_MS = 3_000

# Valid provider names. "local" is the terminal fallback that retains the
# existing validated recording rather than resynthesizing.
PROVIDER_NAMES = frozenset({"openai", "azure", "local"})

# Leading "Speaker: " label on a transcript line. Continuation lines (no label)
# keep the previous speaker's voice.
_SPEAKER_RE = re.compile(r"^([^:]{1,40}):\s+")


class SynthesisError(Exception):
    """A safe provider failure. Never carries secrets or raw response bodies."""


@dataclass(frozen=True)
class WavInfo:
    channels: int
    sample_width: int
    frame_rate: int
    frames: int

    @property
    def duration_ms(self) -> int:
        if self.frame_rate <= 0:
            return 0
        return round(self.frames / self.frame_rate * 1000)


@dataclass(frozen=True)
class SynthesisResult:
    wav_bytes: bytes
    provider: str
    model: str
    voices: tuple[str, ...]
    duration_ms: int
    provenance: str


@dataclass
class ProviderAttempt:
    """Per-provider outcome for operator-facing reporting (no secrets)."""

    name: str
    outcome: str  # "skipped", "error", "invalid", "used"
    detail: str = ""


@dataclass
class SynthesisRun:
    result: SynthesisResult | None
    attempts: list[ProviderAttempt] = field(default_factory=list)


# ── Speaker parsing / voice assignment ──────────────────────────────────────
def parse_dialogue(transcript: str, voice_a: str, voice_b: str) -> list[tuple[str, str]]:
    """Split a transcript into ``(voice, text)`` chunks alternating two voices.

    Distinct speakers are mapped to the two voices in order of first appearance
    (a third speaker cycles back to ``voice_a``). Consecutive lines that resolve
    to the same voice are merged so each chunk is one clean utterance.
    """
    voices = (voice_a, voice_b)
    speaker_voice: dict[str, str] = {}
    current_voice = voice_a
    chunks: list[list[str]] = []

    for raw_line in transcript.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        match = _SPEAKER_RE.match(line)
        if match:
            speaker = match.group(1).strip()
            text = line[match.end() :].strip()
            if speaker not in speaker_voice:
                speaker_voice[speaker] = voices[len(speaker_voice) % 2]
            current_voice = speaker_voice[speaker]
        else:
            text = line
        if not text:
            continue
        if chunks and chunks[-1][0] == current_voice:
            chunks[-1][1] = f"{chunks[-1][1]} {text}"
        else:
            chunks.append([current_voice, text])
    return [(voice, text) for voice, text in chunks]


# ── WAV validation and concatenation (stdlib only) ──────────────────────────
def read_wav_info(data: bytes) -> WavInfo:
    """Parse WAV header info, raising SynthesisError on anything unreadable."""
    try:
        with wave.open(io.BytesIO(data), "rb") as reader:
            if reader.getcomptype() != "NONE":
                raise SynthesisError("Audio is not uncompressed PCM WAV.")
            return WavInfo(
                channels=reader.getnchannels(),
                sample_width=reader.getsampwidth(),
                frame_rate=reader.getframerate(),
                frames=reader.getnframes(),
            )
    except SynthesisError:
        raise
    except (wave.Error, EOFError, OSError, ValueError) as exc:
        raise SynthesisError("Audio is not a valid WAV stream.") from exc


def validate_wav_bytes(data: bytes) -> WavInfo:
    """Strictly validate generated WAV bytes; raise SynthesisError if unusable."""
    if not data:
        raise SynthesisError("Provider returned no audio.")
    if len(data) > MAX_BYTE_SIZE:
        raise SynthesisError("Generated audio exceeds the maximum allowed size.")
    info = read_wav_info(data)
    if info.channels not in (1, 2):
        raise SynthesisError("Generated audio has an unsupported channel count.")
    if info.sample_width not in (1, 2):
        raise SynthesisError("Generated audio has an unsupported sample width.")
    if not (8_000 <= info.frame_rate <= 48_000):
        raise SynthesisError("Generated audio has an unsupported sample rate.")
    if info.frames <= 0:
        raise SynthesisError("Generated audio contains no samples.")
    duration = info.duration_ms
    if duration < max(MIN_DURATION_MS, MIN_GENERATED_DURATION_MS):
        raise SynthesisError("Generated audio is too short to be usable.")
    if duration > MAX_DURATION_MS:
        raise SynthesisError("Generated audio is too long.")
    return info


def concatenate_wav(segments: list[bytes]) -> bytes:
    """Join per-segment WAV clips into one WAV, preserving PCM parameters.

    Every segment must share the same channel count, sample width, frame rate,
    and PCM compression type or a SynthesisError is raised (mismatched headers
    would produce a corrupt file).
    """
    if not segments:
        raise SynthesisError("No audio segments were produced.")
    if len(segments) == 1:
        # Single utterance (e.g. a monologue): validate structure, pass through.
        read_wav_info(segments[0])
        return segments[0]

    params = None
    buffer = io.BytesIO()
    writer: wave.Wave_write | None = None
    try:
        for segment in segments:
            reader = wave.open(io.BytesIO(segment), "rb")
            try:
                seg_params = (
                    reader.getnchannels(),
                    reader.getsampwidth(),
                    reader.getframerate(),
                    reader.getcomptype(),
                )
                if seg_params[3] != "NONE":
                    raise SynthesisError("A segment is not uncompressed PCM WAV.")
                if params is None:
                    params = seg_params
                    writer = wave.open(buffer, "wb")
                    writer.setnchannels(seg_params[0])
                    writer.setsampwidth(seg_params[1])
                    writer.setframerate(seg_params[2])
                elif seg_params != params:
                    raise SynthesisError(
                        "Audio segments have incompatible PCM parameters."
                    )
                writer.writeframes(reader.readframes(reader.getnframes()))
            finally:
                reader.close()
    except SynthesisError:
        raise
    except (wave.Error, EOFError, OSError, ValueError) as exc:
        raise SynthesisError("Could not concatenate audio segments.") from exc
    finally:
        if writer is not None:
            writer.close()
    return buffer.getvalue()


# ── Providers ───────────────────────────────────────────────────────────────
class VoiceProvider(Protocol):
    name: str

    def available(self) -> bool: ...

    def synthesize(self, transcript: str) -> bytes: ...

    def describe(self) -> tuple[str, tuple[str, ...]]:
        """Return ``(model, voices)`` for safe provenance. No secrets."""
        ...


def _today() -> str:
    return date.today().isoformat()


class OpenAIVoiceProvider:
    """Natural OpenAI TTS. Requests WAV output; alternates two voices."""

    name = "openai"

    def __init__(self, *, client=None, model: str | None = None, voices=None):
        self._injected = client is not None
        self._client = client
        self._model = model or settings.OPENAI_TTS_MODEL
        self._voices = tuple(voices or settings.LISTENING_OPENAI_VOICES)

    def available(self) -> bool:
        if len(self._voices) < 2:
            return False
        return self._injected or bool(settings.OPENAI_API_KEY)

    def _get_client(self):
        if self._client is not None:
            return self._client
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover - SDK is a hard dependency
            raise SynthesisError("The OpenAI SDK is not installed.") from exc
        try:
            self._client = OpenAI(
                api_key=settings.OPENAI_API_KEY, timeout=90, max_retries=2
            )
        except Exception as exc:
            # Opaque: constructor failures must not surface key material and must
            # fall through to the next provider like any other provider error.
            raise SynthesisError("OpenAI could not be initialized.") from exc
        return self._client

    def synthesize(self, transcript: str) -> bytes:
        chunks = parse_dialogue(transcript, self._voices[0], self._voices[1])
        if not chunks:
            raise SynthesisError("Transcript produced no speakable text.")
        client = self._get_client()
        clips: list[bytes] = []
        for voice, text in chunks:
            try:
                response = client.audio.speech.create(
                    model=self._model,
                    voice=voice,
                    input=text,
                    response_format="wav",
                )
                clip = response.read()
            except SynthesisError:
                raise
            except Exception as exc:
                # Deliberately opaque: provider bodies may echo the request.
                raise SynthesisError("OpenAI could not synthesize the audio.") from exc
            read_wav_info(clip)
            clips.append(clip)
        return concatenate_wav(clips)

    def describe(self) -> tuple[str, tuple[str, ...]]:
        return self._model, self._voices


class AzureVoiceProvider:
    """Azure Speech neural TTS via the official REST endpoint; RIFF PCM WAV."""

    name = "azure"
    OUTPUT_FORMAT = "riff-16khz-16bit-mono-pcm"

    def __init__(self, *, transport=None, key=None, region=None, voices=None):
        self._injected = transport is not None
        self._transport = transport
        self._key = key if key is not None else settings.AZURE_SPEECH_KEY
        self._region = region if region is not None else settings.AZURE_SPEECH_REGION
        self._voices = tuple(voices or settings.LISTENING_AZURE_VOICES)

    def available(self) -> bool:
        if len(self._voices) < 2:
            return False
        return self._injected or bool(self._key and self._region)

    @property
    def _endpoint(self) -> str:
        return (
            f"https://{self._region}.tts.speech.microsoft.com/"
            "cognitiveservices/v1"
        )

    @staticmethod
    def _ssml(voice: str, text: str) -> str:
        from xml.sax.saxutils import escape

        return (
            '<speak version="1.0" '
            'xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="en-CA">'
            f'<voice name="{escape(voice, {chr(34): "&quot;"})}">'
            f"<prosody rate=\"-3%\">{escape(text)}</prosody>"
            "</voice></speak>"
        )

    def _post(self, ssml: str) -> bytes:
        if self._transport is not None:
            return self._transport(self._endpoint, ssml, self.OUTPUT_FORMAT)
        import urllib.error
        import urllib.request

        try:
            request = urllib.request.Request(
                self._endpoint,
                data=ssml.encode("utf-8"),
                headers={
                    "Ocp-Apim-Subscription-Key": self._key,
                    "Content-Type": "application/ssml+xml",
                    "X-Microsoft-OutputFormat": self.OUTPUT_FORMAT,
                    "User-Agent": "celpip-listening-tts",
                },
                method="POST",
            )
            with urllib.request.urlopen(request, timeout=90) as response:
                return response.read()
        except (urllib.error.URLError, OSError, ValueError) as exc:
            # Never surface the exception body: it can echo headers/URLs. This
            # also converts SSML encode/request-construction errors so they fall
            # through to the next provider like any other provider failure.
            raise SynthesisError("Azure Speech request failed.") from exc

    def synthesize(self, transcript: str) -> bytes:
        chunks = parse_dialogue(transcript, self._voices[0], self._voices[1])
        if not chunks:
            raise SynthesisError("Transcript produced no speakable text.")
        clips: list[bytes] = []
        for voice, text in chunks:
            clip = self._post(self._ssml(voice, text))
            if not clip:
                raise SynthesisError("Azure Speech returned an empty clip.")
            read_wav_info(clip)
            clips.append(clip)
        return concatenate_wav(clips)

    def describe(self) -> tuple[str, tuple[str, ...]]:
        return "azure-speech-neural", self._voices


class LocalRetainProvider:
    """Terminal fallback: keep the existing validated recording.

    The Windows/local PowerShell generator (``scripts/generate-listening-audio``)
    produces the first stored recording. During regeneration this provider does
    not resynthesize (that is Windows-only and not reproducible in CI); instead
    it returns the current on-disk bytes so, when every upstream provider fails,
    the working file is preserved rather than overwritten with something worse.
    """

    name = "local"

    def __init__(self, *, existing_bytes: bytes | None, voice_label: str = ""):
        self._existing = existing_bytes
        self._voice_label = voice_label or "local system-speech voices"

    def available(self) -> bool:
        return self._existing is not None

    def synthesize(self, transcript: str) -> bytes:
        del transcript
        if self._existing is None:
            raise SynthesisError("No existing local recording to retain.")
        return self._existing

    def describe(self) -> tuple[str, tuple[str, ...]]:
        return "local-system-speech", (self._voice_label,)


# ── Orchestration ───────────────────────────────────────────────────────────
def _provenance(provider: str, model: str, voices: tuple[str, ...]) -> str:
    voice_text = ", ".join(voices)
    if provider == "local":
        return (
            f"Retained existing locally synthesized recording ({voice_text}) on "
            f"{_today()}. Synthetic, unofficial practice audio — not an official "
            "CELPIP recording."
        )
    label = {"openai": "OpenAI natural TTS", "azure": "Azure Speech neural TTS"}.get(
        provider, provider
    )
    return (
        f"Generated on {_today()} with {label} (model {model}; voices {voice_text}). "
        "Synthetic, unofficial practice audio produced from an original reviewed "
        "script — not an official CELPIP recording."
    )


def synthesize_listening_audio(
    transcript: str, providers: list[VoiceProvider]
) -> SynthesisRun:
    """Try each provider in order; return the first strictly valid WAV.

    Missing credentials, provider errors, and invalid/corrupt/too-short output
    all fall through to the next provider. The returned run records a
    secret-free attempt log for operator reporting.
    """
    attempts: list[ProviderAttempt] = []
    for provider in providers:
        if not provider.available():
            attempts.append(
                ProviderAttempt(provider.name, "skipped", "credentials or voices absent")
            )
            continue
        try:
            wav_bytes = provider.synthesize(transcript)
        except SynthesisError as exc:
            attempts.append(ProviderAttempt(provider.name, "error", str(exc)))
            continue
        try:
            info = validate_wav_bytes(wav_bytes)
        except SynthesisError as exc:
            attempts.append(ProviderAttempt(provider.name, "invalid", str(exc)))
            continue
        model, voices = provider.describe()
        attempts.append(ProviderAttempt(provider.name, "used"))
        return SynthesisRun(
            result=SynthesisResult(
                wav_bytes=wav_bytes,
                provider=provider.name,
                model=model,
                voices=voices,
                duration_ms=info.duration_ms,
                provenance=_provenance(provider.name, model, voices),
            ),
            attempts=attempts,
        )
    return SynthesisRun(result=None, attempts=attempts)


def build_default_providers(
    order: list[str], *, existing_bytes: bytes | None, existing_voice_label: str = ""
) -> list[VoiceProvider]:
    """Construct the configured providers from settings for the given order."""
    providers: list[VoiceProvider] = []
    for name in order:
        if name not in PROVIDER_NAMES:
            raise SynthesisError(f"Unknown listening TTS provider: {name}")
        if name == "local":
            providers.append(
                LocalRetainProvider(
                    existing_bytes=existing_bytes, voice_label=existing_voice_label
                )
            )
        elif name == "openai":
            providers.append(OpenAIVoiceProvider())
        elif name == "azure":
            providers.append(AzureVoiceProvider())
    return providers
