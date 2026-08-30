from datetime import date

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.accounts.models import User
from apps.content.models import (
    ContentItem,
    ContentVersion,
    SourceType,
    TaskType,
    TestFormatVersion,
)
from apps.content.official_sources import OFFICIAL_FORMAT_SOURCES
from apps.content.services import publish, submit_for_review
from apps.content.speaking_seed_data import SPEAKING_SETS as SPEAKING_SETS_BASE
from apps.content.speaking_seed_data import SPEAKING_TASK_TYPES
from apps.content.speaking_seed_data_v2 import SPEAKING_SETS as SPEAKING_SETS_V2
from apps.content.speaking_seed_data_v3 import SPEAKING_SETS as SPEAKING_SETS_V3


SPEAKING_SETS = SPEAKING_SETS_BASE + SPEAKING_SETS_V2 + SPEAKING_SETS_V3


class Command(BaseCommand):
    help = "Seed the reviewed, original starter Speaking prompt bank idempotently."

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
            identifier="speaking-content-author",
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

        task_types = {}
        for spec in SPEAKING_TASK_TYPES:
            task_type, _ = TaskType.objects.update_or_create(
                code=spec["code"],
                defaults={key: value for key, value in spec.items() if key != "code"},
            )
            task_type.format_versions.add(format_version)
            task_types[task_type.code] = task_type

        created_count = 0
        for spec in SPEAKING_SETS:
            if ContentItem.objects.filter(slug=spec["slug"]).exists():
                continue
            item = ContentItem.objects.create(
                slug=spec["slug"],
                task_type=task_types[spec["task_type"]],
                title=spec["title"],
                topic=spec["topic"],
                difficulty=spec["difficulty"],
                estimated_level=spec["estimated_level"],
                source_type=SourceType.HUMAN_AUTHORED,
                author=author,
                provenance=(
                    "Original speaking prompt authored for this repository and "
                    "reviewed by the project editor on 2026-08-29. No official "
                    "CELPIP prompt, sample response, or paid bank was used."
                ),
            )
            version = ContentVersion.objects.create(
                item=item,
                version=1,
                instructions=spec["instructions"],
                stimulus=spec["stimulus"],
                learning_notes=spec["learning_notes"],
            )
            submit_for_review(version)
            publish(version, reviewer=reviewer)
            created_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Speaking seed ready: {len(SPEAKING_SETS)} sets; created {created_count}."
            )
        )
