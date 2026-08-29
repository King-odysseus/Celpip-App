import time

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.ai_services.services import claim_next_job, run_job


class Command(BaseCommand):
    help = "Process audited AI jobs from the database queue."

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true", help="Process at most one job.")

    def handle(self, *args, **options):
        while True:
            job = claim_next_job()
            if job is not None:
                finished = run_job(job)
                self.stdout.write(f"{finished.id} {finished.kind}: {finished.status}")
            if options["once"]:
                return
            if job is None:
                time.sleep(settings.AI_JOB_POLL_SECONDS)
