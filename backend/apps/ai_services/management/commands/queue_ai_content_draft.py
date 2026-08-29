from django.core.management.base import BaseCommand, CommandError

from apps.ai_services.services import enqueue_content_draft
from apps.content.models import TaskType


class Command(BaseCommand):
    help = "Queue an original AI-assisted objective set for mandatory human review."

    def add_arguments(self, parser):
        parser.add_argument("task_type")
        parser.add_argument("topic")
        parser.add_argument("--difficulty", type=int, default=2)

    def handle(self, *args, **options):
        try:
            task_type = TaskType.objects.get(pk=options["task_type"], is_active=True)
            job = enqueue_content_draft(
                task_type=task_type,
                topic=options["topic"],
                difficulty=options["difficulty"],
            )
        except (TaskType.DoesNotExist, ValueError) as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(self.style.SUCCESS(f"Queued AI draft job {job.id}."))
