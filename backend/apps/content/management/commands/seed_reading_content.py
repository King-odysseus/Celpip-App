from datetime import date

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.accounts.models import User
from apps.content.models import (
    Choice,
    ContentItem,
    ContentVersion,
    Question,
    SourceType,
    TaskType,
    TestFormatVersion,
)
from apps.content.mock_full_length_filler_data import READING_FILLER_SETS
from apps.content.official_sources import OFFICIAL_FORMAT_SOURCES
from apps.content.practice_bank_expansion import expand_practice_bank
from apps.content.reading_seed_data_v2 import READING_SETS as READING_SETS_V2
from apps.content.reading_seed_data_v3 import READING_SETS as READING_SETS_V3
from apps.content.seed_data import READING_SETS as READING_SETS_BASE
from apps.content.seed_data import TASK_TYPES
from apps.content.services import publish, submit_for_review

READING_SOURCE_SETS = READING_SETS_BASE + READING_SETS_V2 + READING_SETS_V3
# Filler sets are not stage-expanded; see mock_full_length_filler_data.py.
READING_SETS = expand_practice_bank(READING_SOURCE_SETS, skill="reading") + READING_FILLER_SETS


class Command(BaseCommand):
    help = "Seed the reviewed, original starter Reading bank idempotently."

    def add_arguments(self, parser):
        parser.add_argument("--reviewer", default="seed-content-reviewer")

    @transaction.atomic
    def handle(self, *args, **options):
        reviewer, reviewer_created = User.objects.get_or_create(
            identifier=options["reviewer"].lower(),
            defaults={"is_staff": True, "is_active": True},
        )
        if not reviewer.is_staff or not reviewer.is_active:
            raise ValueError("The seed reviewer must be active staff.")
        if reviewer_created:
            reviewer.set_unusable_password()
            reviewer.save(update_fields=["password"])

        author, created = User.objects.get_or_create(
            identifier="qwen-assisted-content-author",
            defaults={"is_active": False, "is_staff": False},
        )
        if created:
            author.set_unusable_password()
            author.save(update_fields=["password"])

        format_version, _ = TestFormatVersion.objects.update_or_create(
            code="celpip-general-2026-08",
            defaults={
                "name": "CELPIP-General format verified August 2026",
                "is_active": True,
                "verified_on": date(2026, 8, 29),
                "official_source_urls": OFFICIAL_FORMAT_SOURCES,
                "notes": "Public structural facts only; all seeded practice content is original.",
            },
        )

        task_types: dict[str, TaskType] = {}
        for spec in TASK_TYPES:
            task_type, _ = TaskType.objects.update_or_create(
                code=spec["code"],
                defaults={key: value for key, value in spec.items() if key != "code"},
            )
            task_type.format_versions.add(format_version)
            task_types[task_type.code] = task_type

        created_count = 0
        for spec in READING_SETS:
            if ContentItem.objects.filter(slug=spec["slug"]).exists():
                continue
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
                    "Original Qwen-assisted draft created for this repository; "
                    "reviewed and corrected by the project architect on 2026-08-29. "
                    "No official question, sample response, transcript, or paid bank was used."
                ),
            )
            version = ContentVersion.objects.create(
                item=item,
                version=1,
                instructions=spec["instructions"],
                stimulus=spec["stimulus"],
                learning_notes=spec["learning_notes"],
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
            created_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Reading seed ready: {len(READING_SETS)} sets; created {created_count}."
            )
        )
