"""Generate one illustration per Speaking scene/prediction/unusual-object concept.

Uses the already-configured server-side ``OPENAI_API_KEY`` (the same one the
live Speaking/Writing feedback pipeline uses) via ``OpenAIProvider.generate_image``.
Run this where that key is available — typically production — and copy the
resulting files back into ``frontend/public/speaking/``:

    railway run python backend/manage.py generate_speaking_images \\
        --out-dir frontend/public/speaking

``railway run`` executes the command *locally*, using Railway's environment
variables, so the generated files land directly in your working tree — no
manual download step. From inside ``backend/``, pass a relative out-dir such
as ``../frontend/public/speaking`` instead.

Saved as PNG (the OpenAI images API returns PNG); no image library is
required. Files are noticeably larger than the hand-optimized WebP originals
this replaces — convert them yourself afterward if you want WebP's smaller
size, or update the seed data / migration to point at ``.webp`` filenames
once you have converted copies.

After the files exist and are committed:
- A fresh database seeds every Speaking item with its own new image already.
- An already-seeded database needs its stored, published
  ``ContentVersion.stimulus.image_url`` values rewritten — that is what the
  ``0005_speaking_unique_scene_images`` migration does; run
  ``python manage.py migrate`` after deploying the new files.
"""
from __future__ import annotations

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.ai_services.contracts import ProviderError
from apps.ai_services.providers import OpenAIProvider
from apps.content.speaking_scene_images import SPEAKING_IMAGE_CONCEPTS


class Command(BaseCommand):
    help = "Generate one illustration per Speaking scene/prediction/unusual-object concept."

    def add_arguments(self, parser):
        parser.add_argument(
            "--out-dir",
            required=True,
            help="Directory to write the generated PNG files into (created if missing).",
        )
        parser.add_argument(
            "--filename",
            default=None,
            help="Limit to the concept with this filename (see speaking_scene_images.py).",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Regenerate even when a file for that concept already exists.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="List what would be generated without calling the provider.",
        )

    def handle(self, *args, **options):
        out_dir = Path(options["out_dir"])
        filename = options["filename"]
        force = options["force"]
        dry_run = options["dry_run"]

        concepts = SPEAKING_IMAGE_CONCEPTS
        if filename:
            concepts = [c for c in concepts if c.filename == filename]
            if not concepts:
                raise CommandError(f"No image concept with filename {filename!r}.")

        if dry_run:
            for concept in concepts:
                target = out_dir / f"{concept.filename}.png"
                exists = target.is_file()
                self.stdout.write(
                    f"  {concept.filename}: {'exists — would skip' if exists and not force else 'would generate'} "
                    f"(members: {', '.join(concept.member_slugs)})"
                )
            self.stdout.write(self.style.SUCCESS(f"Dry run done. {len(concepts)} concept(s)."))
            return

        try:
            provider = OpenAIProvider()
        except ProviderError as exc:
            raise CommandError(f"OpenAI is not available: {exc}") from exc

        out_dir.mkdir(parents=True, exist_ok=True)
        generated = skipped = failed = 0
        for concept in concepts:
            target = out_dir / f"{concept.filename}.png"
            if target.is_file() and not force:
                skipped += 1
                self.stdout.write(f"  {concept.filename}: already exists — skipped.")
                continue
            try:
                image_bytes = provider.generate_image(concept.prompt)
            except ProviderError as exc:
                failed += 1
                self.stderr.write(self.style.ERROR(f"  {concept.filename}: failed ({exc})."))
                continue
            target.write_bytes(image_bytes)
            generated += 1
            self.stdout.write(
                self.style.SUCCESS(f"  {concept.filename}: generated ({len(image_bytes)} bytes).")
            )

        summary = f"Done. generated={generated} skipped={skipped} failed={failed}."
        self.stdout.write(self.style.SUCCESS(summary) if not failed else summary)
        if failed:
            raise CommandError(f"{failed} image(s) could not be generated.")
