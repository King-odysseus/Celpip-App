"""Refresh stored Listening transcripts from the committed seed modules.

``seed_listening_content`` writes each ``MediaAsset.transcript`` once and then
skips any item whose asset already exists, so a database seeded before a script
rewrite keeps the old text forever. This command closes that gap for existing
assets: it re-reads the same ``LISTENING_SETS`` the seed uses and updates only
the stored ``transcript`` (and ``speaker_genders`` when a spec defines it) for
assets that already exist.

Audio files, checksums, voice labels, and provenance are deliberately left
untouched — this command moves the *script* forward without touching the
recording. Run ``regenerate_listening_audio`` afterwards to synthesize the new
script into natural voices.

Examples::

    python manage.py sync_listening_transcripts --dry-run
    python manage.py sync_listening_transcripts --slug weekend-market-produce-shortage
    python manage.py sync_listening_transcripts
"""
from __future__ import annotations

from django.core.management.base import BaseCommand

from apps.content.management.commands.seed_listening_content import LISTENING_SETS
from apps.media_assets.models import MediaAsset


class Command(BaseCommand):
    help = "Refresh stored Listening transcripts from the committed seed modules."

    def add_arguments(self, parser):
        parser.add_argument(
            "--slug",
            default=None,
            help="Limit to the ContentItem with this slug (default: all Listening audio).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report the changes without writing to the database.",
        )

    def handle(self, *args, **options):
        slug = options["slug"]
        dry_run = options["dry_run"]

        manifest = {spec["slug"]: spec for spec in LISTENING_SETS}
        assets = MediaAsset.objects.filter(
            content_version__version=1,
            content_version__item__task_type__skill="listening",
        ).select_related("content_version__item")
        if slug:
            assets = assets.filter(content_version__item__slug=slug)

        updated = unchanged = missing = 0
        for asset in assets:
            item_slug = asset.content_version.item.slug
            spec = manifest.get(item_slug)
            if spec is None:
                # The asset exists but no seed spec backs it; report and leave
                # it exactly as it is rather than guessing at a script.
                missing += 1
                self.stdout.write(f"  {item_slug}: no seed spec — skipped.")
                continue

            transcript = spec["transcript"]
            transcript_changed = asset.transcript != transcript
            # A spec without ``speaker_genders`` carries no opinion about the
            # field, so an existing value is left untouched (like the seed, the
            # field only lands on a value when the spec actually defines one).
            has_genders = "speaker_genders" in spec
            genders_changed = has_genders and asset.speaker_genders != spec["speaker_genders"]

            if not (transcript_changed or genders_changed):
                unchanged += 1
                continue

            changed = []
            if transcript_changed:
                changed.append("transcript")
            if genders_changed:
                changed.append("speaker_genders")

            if dry_run:
                updated += 1
                self.stdout.write(
                    f"  {item_slug}: would update {', '.join(changed)}"
                )
                continue

            update_fields = []
            if transcript_changed:
                asset.transcript = transcript
                update_fields.append("transcript")
            if genders_changed:
                asset.speaker_genders = spec["speaker_genders"]
                update_fields.append("speaker_genders")
            asset.save(update_fields=update_fields)
            updated += 1
            self.stdout.write(
                self.style.SUCCESS(f"  {item_slug}: updated {', '.join(changed)}")
            )

        if dry_run:
            self.stdout.write(
                f"{updated} would update, {unchanged} in sync, {missing} missing."
            )
            return

        summary = f"Done. updated={updated} unchanged={unchanged} missing={missing}."
        self.stdout.write(self.style.SUCCESS(summary) if not missing else summary)
