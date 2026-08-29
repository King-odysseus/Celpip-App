from django.core.management.base import BaseCommand, CommandError

from apps.content.models import ContentVersion
from apps.content.services import validate_content_version


class Command(BaseCommand):
    help = "Validate authored content and fail when any version is incomplete."

    def add_arguments(self, parser):
        parser.add_argument("--published-only", action="store_true")

    def handle(self, *args, **options):
        versions = ContentVersion.objects.select_related("item").prefetch_related(
            "questions__choices"
        )
        if options["published_only"]:
            versions = versions.filter(status="published")

        failures = 0
        for version in versions:
            issues = validate_content_version(version)
            for issue in issues:
                failures += 1
                self.stderr.write(
                    f"{version.item.slug} v{version.version}: "
                    f"{issue.code}: {issue.message}"
                )
        if failures:
            raise CommandError(f"Content validation failed with {failures} issue(s).")
        self.stdout.write(self.style.SUCCESS(f"Validated {versions.count()} content version(s)."))
