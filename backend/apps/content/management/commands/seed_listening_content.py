import shutil
import wave
from datetime import date
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.accounts.models import User
from apps.content.listening_official_parts import LISTENING_OFFICIAL_SETS
from apps.content.listening_official_parts_v2 import LISTENING_OFFICIAL_SETS_V2
from apps.content.listening_seed_data import LISTENING_SETS as LISTENING_SETS_BASE
from apps.content.listening_seed_data import LISTENING_TASK_TYPES
from apps.content.listening_seed_data_v2 import LISTENING_SETS as LISTENING_SETS_V2
from apps.content.listening_seed_data_v3 import LISTENING_SETS as LISTENING_SETS_V3
from apps.content.mock_full_length_filler_data import LISTENING_FILLER_SETS
from apps.content.models import (
    Choice,
    ContentItem,
    ContentVersion,
    Question,
    SourceType,
    TaskType,
    TestFormatVersion,
)
from apps.content.official_sources import OFFICIAL_FORMAT_SOURCES
from apps.content.practice_bank_expansion import expand_practice_bank
from apps.content.services import publish, submit_for_review
from apps.media_assets.models import MediaAsset, MediaStatus
from apps.media_assets.services import file_checksum

LISTENING_SOURCE_SETS = LISTENING_SETS_BASE + LISTENING_SETS_V2 + LISTENING_SETS_V3
# Filler sets are deliberately NOT stage-expanded: they exist only to let the
# full-length mock hit an exact official question count (see
# mock_full_length_filler_data.py) and are excluded from that expansion so
# their audio stays to one file each rather than four. Official-part sets are
# likewise not stage-expanded: each is a complete official Listening part (one
# recording, full question count) that a full-length mock should use as-is.
LISTENING_SETS = (
    expand_practice_bank(LISTENING_SOURCE_SETS, skill="listening")
    + LISTENING_FILLER_SETS
    + LISTENING_OFFICIAL_SETS
    + LISTENING_OFFICIAL_SETS_V2
)


class Command(BaseCommand):
    help = "Seed reviewed original Listening sets and their private audio metadata."

    def add_arguments(self, parser):
        parser.add_argument("--reviewer", default="seed-content-reviewer")

    @transaction.atomic
    def handle(self, *args, **options):
        reviewer, reviewer_created = User.objects.get_or_create(
            identifier=options["reviewer"].lower(),
            defaults={"is_staff": True, "is_active": True},
        )
        if not reviewer.is_staff or not reviewer.is_active:
            raise CommandError("The seed reviewer must be active staff.")
        if reviewer_created:
            reviewer.set_unusable_password()
            reviewer.save(update_fields=["password"])

        author, author_created = User.objects.get_or_create(
            identifier="qwen-assisted-content-author",
            defaults={"is_active": False, "is_staff": False},
        )
        if author_created:
            author.set_unusable_password()
            author.save(update_fields=["password"])

        format_version, _ = TestFormatVersion.objects.update_or_create(
            code="celpip-general-2026-08",
            defaults={
                "name": "CELPIP-General format verified August 2026",
                "is_active": True,
                "verified_on": date(2026, 8, 29),
                "official_source_urls": OFFICIAL_FORMAT_SOURCES,
                "notes": "Public format facts only; practice scripts and audio are original.",
            },
        )
        task_types = {}
        for spec in LISTENING_TASK_TYPES:
            task_type, _ = TaskType.objects.update_or_create(
                code=spec["code"],
                defaults={key: value for key, value in spec.items() if key != "code"},
            )
            task_type.format_versions.add(format_version)
            task_types[task_type.code] = task_type

        created_count = 0
        for spec in LISTENING_SETS:
            audio_slug = spec.get("audio_slug", spec["slug"])
            audio_path = self._audio_path(audio_slug)
            if not audio_path.is_file():
                source_slug = spec.get("source_slug")
                source_path = self._audio_path(source_slug) if source_slug else None
                if source_path and source_path.is_file():
                    # A fresh production volume may be bootstrapped before the
                    # optional expanded WAV bundle is mounted. Materialize a
                    # safe fallback so startup remains available; generated
                    # stage recordings take precedence whenever present.
                    audio_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(source_path, audio_path)
                else:
                    raise CommandError(
                        f"Missing {audio_path}. Run scripts/generate-listening-audio.ps1 first."
                    )
            item = ContentItem.objects.filter(slug=spec["slug"]).first()
            if item is None:
                item = self._create_item(spec, task_types, author, reviewer)
                created_count += 1
            version = item.versions.get(version=1)
            if MediaAsset.objects.filter(content_version=version).exists():
                continue
            duration_ms = self._wav_duration_ms(audio_path)
            MediaAsset.objects.create(
                content_version=version,
                storage_key=f"listening/{audio_slug}.wav",
                mime_type="audio/wav",
                byte_size=audio_path.stat().st_size,
                duration_ms=duration_ms,
                checksum_sha256=file_checksum(audio_path),
                transcript=spec["transcript"],
                speaker_genders=spec.get("speaker_genders"),
                voice_label="Synthetic Canadian-English development voice",
                provenance=(
                    "Original repository script, architect-reviewed on 2026-08-29; "
                    "locally synthesized with installed operating-system voices."
                ),
                status=MediaStatus.READY,
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Listening seed ready: {len(LISTENING_SETS)} sets; created {created_count}."
            )
        )

    def _create_item(self, spec, task_types, author, reviewer):
        item = ContentItem.objects.create(
            slug=spec["slug"],
            task_type=task_types[spec["task_type"]],
            title=spec["title"],
            topic=spec["topic"],
            difficulty=spec["difficulty"],
            estimated_level=spec["estimated_level"],
            source_type=SourceType.AI_GENERATED,
            author=author,
            provenance=(
                "Original Qwen-assisted concept expanded and corrected by the project architect; "
                "no official question, recording, transcript, or paid bank was used."
            ),
        )
        version = ContentVersion.objects.create(
            item=item,
            version=1,
            instructions=spec["instructions"],
            stimulus={
                "type": "audio_context",
                "introduction": spec["intro"],
                "practice_adaptation": True,
            },
            learning_notes=(
                "Set up brief notes before playing. Focus on meaning, speaker purpose, "
                "and paraphrase rather than trying to write every word."
            ),
        )
        for question_order, question_spec in enumerate(spec["questions"], start=1):
            question = Question.objects.create(
                content_version=version,
                order=question_order,
                stem=question_spec["stem"],
                skill_focus=question_spec["skill_focus"],
                evidence=question_spec["evidence"],
                explanation=question_spec["explanation"],
            )
            for choice_order, choice_spec in enumerate(question_spec["choices"], start=1):
                Choice.objects.create(
                    question=question,
                    order=choice_order,
                    text=choice_spec["text"],
                    is_correct=choice_spec["is_correct"],
                    explanation=choice_spec["explanation"],
                )
        submit_for_review(version)
        publish(version, reviewer=reviewer)
        return item

    def _audio_path(self, slug: str) -> Path:
        return Path(settings.PRIVATE_MEDIA_ROOT) / "listening" / f"{slug}.wav"

    def _wav_duration_ms(self, path: Path) -> int:
        with wave.open(str(path), "rb") as audio:
            return round(audio.getnframes() / audio.getframerate() * 1000)
