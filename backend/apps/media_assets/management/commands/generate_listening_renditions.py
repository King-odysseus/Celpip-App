"""Generate per-provider Listening audio renditions without touching canonical WAVs.

Unlike ``regenerate_listening_audio``, which rewrites the canonical MediaAsset
through a provider *order*, this command produces an alternative
:class:`~apps.media_assets.models.AudioRendition` for one or more specific
remote providers. It never falls back to another vendor and never uses the
``local`` provider: only the requested ``openai`` or ``azure`` provider is
instantiated, and the canonical WAV is left exactly as-is.

Each rendition is written to a deterministic private path —
``listening_renditions/{provider}/{canonical asset uuid}.wav`` — atomically
(temp file + ``os.replace``) and only after strict WAV validation. A database
failure restores the prior file so on-disk content and metadata never diverge.
Synthesis is idempotent: when the deterministic provider returns bytes whose
checksum matches an existing READY rendition, nothing is rewritten.

Examples::

    python manage.py generate_listening_renditions --provider openai
    python manage.py generate_listening_renditions --provider openai,azure \
        --slug apartment-heating-plan
    python manage.py generate_listening_renditions --provider openai --provider azure --force
    python manage.py generate_listening_renditions --provider openai --dry-run
"""
from __future__ import annotations

import hashlib
import os
import tempfile
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.media_assets.audio_synthesis import (
    AzureVoiceProvider,
    OpenAIVoiceProvider,
    SynthesisError,
    synthesize_listening_audio,
    validate_wav_bytes,
)
from apps.media_assets.models import AudioRendition, MediaAsset, MediaStatus
from apps.media_assets.services import private_media_path

# The only providers this command may instantiate. "local" is deliberately
# absent so a rendition can never silently fall back to retaining the canonical.
REMOTE_PROVIDERS = {"openai": OpenAIVoiceProvider, "azure": AzureVoiceProvider}


def build_rendition_provider(name: str):
    """Instantiate exactly one requested remote provider; never a local fallback."""
    if name == "azure":
        raise SynthesisError("Azure TTS is disabled. Use OpenAI or local audio.")
    if name not in REMOTE_PROVIDERS:
        raise SynthesisError(f"Unsupported rendition provider: {name}")
    return REMOTE_PROVIDERS[name]()


class Command(BaseCommand):
    help = "Generate remote-provider Listening audio renditions, leaving canonical WAVs untouched."

    def add_arguments(self, parser):
        parser.add_argument(
            "--provider",
            action="append",
            default=[],
            help="Remote provider to synthesize: openai or azure. Repeatable or comma-separated.",
        )
        parser.add_argument(
            "--slug",
            default=None,
            help="Limit to the ContentItem with this slug (default: all Listening audio).",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Resynthesize even when the rendition already exists and is valid.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report the plan and provider availability without calling any provider.",
        )

    def handle(self, *args, **options):
        providers = self._parse_providers(options["provider"])
        slug = options["slug"]
        force = options["force"]
        dry_run = options["dry_run"]

        assets = MediaAsset.objects.filter(
            content_version__item__task_type__skill="listening"
        ).select_related("content_version__item")
        if slug:
            assets = assets.filter(content_version__item__slug=slug)
        assets = list(assets)
        if not assets:
            raise CommandError(
                f"No Listening audio found{f' for slug {slug!r}' if slug else ''}."
            )

        self.stdout.write(f"Providers: {', '.join(providers)}")
        generated = unchanged = skipped = unavailable = failed = 0

        for asset in assets:
            item_slug = asset.content_version.item.slug
            for provider_name in providers:
                rendition = AudioRendition.objects.filter(
                    canonical_asset=asset, provider=provider_name
                ).first()
                existing_bytes, existing_valid = self._load_existing(rendition)

                if (
                    not force
                    and existing_valid
                    and rendition is not None
                    and rendition.status == MediaStatus.READY
                ):
                    skipped += 1
                    self.stdout.write(
                        f"  {item_slug}/{provider_name}: already valid — skipped."
                    )
                    continue

                provider = build_rendition_provider(provider_name)

                if dry_run:
                    self.stdout.write(
                        f"  {item_slug}/{provider_name}: would synthesize "
                        f"(provider available={provider.available()})."
                    )
                    continue

                run = synthesize_listening_audio(asset.transcript, [provider])
                for attempt in run.attempts:
                    self.stdout.write(
                        f"    [{item_slug}/{provider_name}] {attempt.name}: {attempt.outcome}"
                        + (f" ({attempt.detail})" if attempt.detail else "")
                    )

                if run.result is None:
                    if any(a.outcome == "skipped" for a in run.attempts):
                        unavailable += 1
                        self.stdout.write(
                            f"  {item_slug}/{provider_name}: provider unavailable "
                            "(missing credentials) — no changes."
                        )
                    else:
                        failed += 1
                        self.stderr.write(
                            self.style.ERROR(
                                f"  {item_slug}/{provider_name}: provider produced no valid "
                                "audio — no changes."
                            )
                        )
                    continue

                result = run.result
                new_checksum = hashlib.sha256(result.wav_bytes).hexdigest()
                if (
                    existing_valid
                    and rendition is not None
                    and rendition.status == MediaStatus.READY
                    and new_checksum == rendition.checksum_sha256
                ):
                    unchanged += 1
                    self.stdout.write(
                        f"  {item_slug}/{provider_name}: produced identical audio — unchanged."
                    )
                    continue

                try:
                    self._place_and_record(
                        asset, provider_name, result, new_checksum, existing_bytes
                    )
                except Exception as exc:
                    # A single asset/provider's filesystem or DB failure must not
                    # abort the batch; _place_and_record has already restored the
                    # prior file (or removed the new one) on failure.
                    failed += 1
                    self.stderr.write(
                        self.style.ERROR(
                            f"  {item_slug}/{provider_name}: update failed ({exc}); "
                            "existing rendition left untouched."
                        )
                    )
                    continue
                generated += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  {item_slug}/{provider_name}: generated "
                        f"({result.duration_ms} ms, {len(result.wav_bytes)} bytes)."
                    )
                )

        summary = (
            f"Done. generated={generated} unchanged={unchanged} skipped={skipped} "
            f"unavailable={unavailable} failed={failed}."
        )
        self.stdout.write(self.style.SUCCESS(summary) if not failed else summary)
        if failed:
            raise CommandError(f"{failed} rendition(s) could not be generated.")

    # ── helpers ──────────────────────────────────────────────────────────────
    def _parse_providers(self, raw: list[str]) -> list[str]:
        requested: list[str] = []
        for chunk in raw:
            requested.extend(name.strip() for name in chunk.split(",") if name.strip())
        if not requested:
            raise CommandError("Provide at least one --provider (openai only).")
        unknown = [name for name in requested if name not in REMOTE_PROVIDERS]
        if unknown:
            raise CommandError(
                f"Unknown rendition provider(s): {', '.join(unknown)}. "
                f"Valid options are {', '.join(sorted(REMOTE_PROVIDERS))}."
            )
        # Deduplicate while preserving order.
        return list(dict.fromkeys(requested))

    @staticmethod
    def _rendition_storage_key(asset: MediaAsset, provider_name: str) -> str:
        return f"listening_renditions/{provider_name}/{asset.id}.wav"

    def _load_existing(
        self, rendition: AudioRendition | None
    ) -> tuple[bytes | None, bool]:
        if rendition is None:
            return None, False
        try:
            path = private_media_path(rendition.storage_key)
        except Exception:
            return None, False
        if not path.is_file():
            return None, False
        try:
            data = path.read_bytes()
        except OSError:
            return None, False
        try:
            validate_wav_bytes(data)
        except SynthesisError:
            return data, False
        return data, True

    def _place_and_record(
        self,
        asset: MediaAsset,
        provider_name: str,
        result,
        new_checksum: str,
        original_bytes: bytes | None,
    ) -> None:
        storage_key = self._rendition_storage_key(asset, provider_name)
        target = private_media_path(storage_key)
        # Place the file first (atomic), then create/update the row. If the row
        # write fails the file is restored so on-disk content and metadata never
        # diverge, and a previously working rendition is never silently lost.
        self._atomic_write(target, result.wav_bytes)
        try:
            with transaction.atomic():
                rendition = AudioRendition.objects.filter(
                    canonical_asset=asset, provider=provider_name
                ).first()
                if rendition is None:
                    rendition = AudioRendition(
                        canonical_asset=asset, provider=provider_name
                    )
                rendition.storage_key = storage_key
                rendition.mime_type = "audio/wav"
                rendition.byte_size = len(result.wav_bytes)
                rendition.duration_ms = result.duration_ms
                rendition.checksum_sha256 = new_checksum
                rendition.model_name = result.model
                rendition.voice_label = ", ".join(result.voices)[:120]
                rendition.provenance = result.provenance
                rendition.status = MediaStatus.READY
                rendition.full_clean()
                rendition.save(
                    update_fields=[
                        "storage_key",
                        "mime_type",
                        "byte_size",
                        "duration_ms",
                        "checksum_sha256",
                        "model_name",
                        "voice_label",
                        "provenance",
                        "status",
                    ]
                )
        except BaseException:
            self._restore(target, original_bytes)
            raise

    @staticmethod
    def _restore(target: Path, original_bytes: bytes | None) -> None:
        """Return the on-disk file to its prior state after a failed DB write."""
        if original_bytes is None:
            try:
                target.unlink()
            except FileNotFoundError:
                pass
            return
        Command._atomic_write(target, original_bytes)

    @staticmethod
    def _atomic_write(target: Path, data: bytes) -> None:
        target.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(dir=str(target.parent), suffix=".wav.tmp")
        try:
            with os.fdopen(fd, "wb") as tmp_file:
                tmp_file.write(data)
                tmp_file.flush()
                os.fsync(tmp_file.fileno())
            os.replace(tmp_name, target)
        except BaseException:
            if os.path.exists(tmp_name):
                os.unlink(tmp_name)
            raise
