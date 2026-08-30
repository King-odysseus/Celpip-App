"""Safely regenerate stored Listening audio from reviewed transcripts.

Tries the configured provider order (default ``openai,azure,local``) per asset
and only replaces the on-disk WAV — atomically, after strict validation — when a
provider returns valid audio. A working recording is never overwritten or
destroyed when every upstream provider fails; the MediaAsset row is updated only
after the file has been placed successfully.

Examples::

    python manage.py regenerate_listening_audio --dry-run
    python manage.py regenerate_listening_audio --slug apartment-heating-plan --force
    python manage.py regenerate_listening_audio --force
    python manage.py regenerate_listening_audio --only-local
"""
from __future__ import annotations

import hashlib
import os
import tempfile
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.media_assets.audio_synthesis import (
    PROVIDER_NAMES,
    SynthesisError,
    build_default_providers,
    synthesize_listening_audio,
    validate_wav_bytes,
)
from apps.media_assets.models import MediaAsset, MediaStatus
from apps.media_assets.services import private_media_path


class Command(BaseCommand):
    help = "Regenerate stored Listening audio via the configured TTS provider order."

    def add_arguments(self, parser):
        parser.add_argument(
            "--slug",
            default=None,
            help="Limit to the ContentItem with this slug (default: all Listening audio).",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Resynthesize even when the current recording is already valid.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report the plan and provider availability without calling any provider.",
        )
        parser.add_argument(
            "--provider-order",
            default=None,
            help=(
                "Comma-separated override of LISTENING_TTS_PROVIDER_ORDER "
                "(e.g. 'azure,openai,local')."
            ),
        )
        parser.add_argument(
            "--only-local",
            action="store_true",
            help=(
                "Regenerate only assets whose current audio is locally/OS-synthesized "
                "development audio; remote (OpenAI/Azure) recordings are left untouched. "
                "Implies --force for matching assets, so a valid local recording is "
                "replaced rather than skipped. Safe to run on every deploy."
            ),
        )

    def handle(self, *args, **options):
        slug = options["slug"]
        force = options["force"]
        dry_run = options["dry_run"]
        only_local = options["only_local"]
        order = (
            [name.strip() for name in options["provider_order"].split(",") if name.strip()]
            if options["provider_order"]
            else list(settings.LISTENING_TTS_PROVIDER_ORDER)
        )
        if not order:
            raise CommandError("No listening TTS provider order is configured.")
        unknown = [name for name in order if name not in PROVIDER_NAMES]
        if unknown:
            raise CommandError(
                f"Unknown listening TTS provider(s): {', '.join(unknown)}. "
                f"Valid options are {', '.join(sorted(PROVIDER_NAMES))}."
            )

        assets = MediaAsset.objects.filter(
            content_version__item__task_type__skill="listening"
        ).select_related("content_version__item")
        if slug:
            assets = assets.filter(content_version__item__slug=slug)
        assets = list(assets)
        if only_local:
            assets = [asset for asset in assets if self._is_local_audio(asset)]
        if not assets:
            if only_local:
                self.stdout.write(
                    self.style.SUCCESS(
                        "No local-synthesized listening audio to regenerate."
                    )
                )
                return
            raise CommandError(
                f"No Listening audio found{f' for slug {slug!r}' if slug else ''}."
            )

        self.stdout.write(f"Provider order: {', '.join(order)}")
        regenerated = repaired = unchanged = skipped = failed = 0

        for asset in assets:
            item_slug = asset.content_version.item.slug
            existing_bytes, existing_valid = self._load_existing(asset)

            if (
                not force
                and not only_local
                and existing_valid
                and asset.status == MediaStatus.READY
            ):
                skipped += 1
                self.stdout.write(f"  {item_slug}: already valid — skipped.")
                continue

            if dry_run:
                action = "regenerate" if (force or only_local) else "repair"
                providers = build_default_providers(
                    order,
                    existing_bytes=existing_bytes if existing_valid else None,
                    existing_voice_label=asset.voice_label,
                )
                availability = ", ".join(
                    f"{provider.name}={provider.available()}" for provider in providers
                )
                self.stdout.write(
                    f"  {item_slug}: would {action} (current file "
                    f"{'valid' if existing_valid else 'missing/invalid'}; "
                    f"providers: {availability})."
                )
                continue

            providers = build_default_providers(
                order,
                existing_bytes=existing_bytes if existing_valid else None,
                existing_voice_label=asset.voice_label,
            )
            run = synthesize_listening_audio(asset.transcript, providers)
            for attempt in run.attempts:
                self.stdout.write(f"    [{item_slug}] {attempt.name}: {attempt.outcome}"
                                  + (f" ({attempt.detail})" if attempt.detail else ""))

            if run.result is None:
                failed += 1
                self.stderr.write(
                    self.style.ERROR(
                        f"  {item_slug}: no provider produced valid audio — "
                        "existing recording left untouched."
                    )
                )
                continue

            result = run.result
            new_checksum = hashlib.sha256(result.wav_bytes).hexdigest()
            if (
                existing_valid
                and asset.status == MediaStatus.READY
                and new_checksum == asset.checksum_sha256
            ):
                unchanged += 1
                self.stdout.write(
                    f"  {item_slug}: {result.provider} produced identical audio — unchanged."
                )
                continue

            try:
                self._place_and_record(asset, result, new_checksum, existing_bytes)
            except Exception as exc:
                # A single asset's filesystem/DB failure must not abort the batch;
                # _place_and_record has already restored the prior file on a DB
                # failure and left it untouched on a write failure.
                failed += 1
                self.stderr.write(
                    self.style.ERROR(
                        f"  {item_slug}: update failed ({exc}); "
                        "existing recording left untouched."
                    )
                )
                continue
            if result.provider == "local":
                repaired += 1
            else:
                regenerated += 1
            self.stdout.write(
                self.style.SUCCESS(
                    f"  {item_slug}: updated via {result.provider} "
                    f"({result.duration_ms} ms, {len(result.wav_bytes)} bytes)."
                )
            )

        summary = (
            f"Done. regenerated={regenerated} repaired={repaired} "
            f"unchanged={unchanged} skipped={skipped} failed={failed}."
        )
        self.stdout.write(self.style.SUCCESS(summary) if not failed else summary)
        if failed:
            raise CommandError(f"{failed} asset(s) could not be regenerated.")

    # ── helpers ──────────────────────────────────────────────────────────────
    @staticmethod
    def _is_local_audio(asset: MediaAsset) -> bool:
        """True when the stored audio came from OS/local speech, not a remote provider.

        The seed records the locally synthesized development voice, and the
        terminal ``local`` provider's provenance marks retained recordings the
        same way. OpenAI/Azure provenance never contains these markers.
        """
        label = (asset.voice_label or "").lower()
        provenance = (asset.provenance or "").lower()
        return (
            "development voice" in label
            or "locally synthesized" in provenance
            or "local system-speech" in provenance
        )

    def _load_existing(self, asset: MediaAsset) -> tuple[bytes | None, bool]:
        try:
            path = private_media_path(asset.storage_key)
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
        self, asset: MediaAsset, result, new_checksum: str, original_bytes: bytes | None
    ) -> None:
        target = private_media_path(asset.storage_key)
        # Replace the file first (atomic), then update the row. If the row update
        # fails the file is restored so on-disk content and metadata never diverge
        # and a previously working recording is never silently destroyed.
        self._atomic_write(target, result.wav_bytes)
        try:
            with transaction.atomic():
                locked = MediaAsset.objects.select_for_update().get(pk=asset.pk)
                locked.mime_type = "audio/wav"
                locked.byte_size = len(result.wav_bytes)
                locked.duration_ms = result.duration_ms
                locked.checksum_sha256 = new_checksum
                locked.voice_label = ", ".join(result.voices)[:120]
                locked.provenance = result.provenance
                locked.status = MediaStatus.READY
                locked.full_clean(exclude=["content_version"])
                locked.save(
                    update_fields=[
                        "mime_type",
                        "byte_size",
                        "duration_ms",
                        "checksum_sha256",
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
        """Return the on-disk file to its prior state after a failed DB update."""
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
