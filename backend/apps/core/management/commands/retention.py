"""Retention purge for expired guest data and stale failed AI jobs.

Runs as a safe dry-run by default; passing ``--execute`` performs the deletions.
Age thresholds are bounded so a typo cannot sweep up fresh data, and each
deletion is chunked to keep transactions small.
"""
from __future__ import annotations

from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.ai_services.models import AIFeedback, AIJob, AIJobStatus
from apps.assessments.models import AssessmentSession

# Bounds (inclusive) for the age arguments, chosen to be generous but safe.
MIN_GUEST_EXPIRED_HOURS = 1
MAX_GUEST_EXPIRED_HOURS = 720
MIN_AI_FAILED_DAYS = 1
MAX_AI_FAILED_DAYS = 3650
MIN_BATCH_SIZE = 1
MAX_BATCH_SIZE = 10_000


def _purge_guest_sessions(sessions, batch_size: int) -> tuple[int, int]:
    """Delete expired guest sessions, cascading their private recordings.

    The ``AIFeedback.job`` PROTECT edge is cleared first so the cascade (session
    -> item -> feedback/job) can proceed; deleting a speaking session also
    removes its audio file via the existing post_delete signal.

    Returns ``(sessions_deleted, feedback_deleted)`` as true row counts: the
    number of sessions removed and the number of linked feedback rows cleared,
    *not* Django's cascade total (which also counts items/responses/jobs).
    """
    total_sessions = 0
    total_feedback = 0
    while True:
        pks = list(sessions.values_list("pk", flat=True)[:batch_size])
        if not pks:
            break
        total_feedback += AIFeedback.objects.filter(
            session_item__session_id__in=pks
        ).delete()[0]
        total_sessions += len(pks)
        AssessmentSession.objects.filter(pk__in=pks).delete()
    return total_sessions, total_feedback


def _purge_failed_jobs(jobs, batch_size: int) -> tuple[int, int]:
    """Delete stale failed AI jobs after clearing their PROTECTed feedback.

    ``AIFeedback.job`` uses ``on_delete=PROTECT``, so deleting a job that still
    has feedback would raise ``ProtectedError``. The feedback rows pointing at
    the selected jobs are removed first, then the jobs themselves. Only the
    selected stale FAILED jobs (and their own feedback) are touched; successful,
    running, queued, and unrelated feedback rows are never removed.

    Returns ``(jobs_deleted, feedback_deleted)`` as true row counts, not the
    cascade total from Django's ``.delete()``.
    """
    total_jobs = 0
    total_feedback = 0
    while True:
        pks = list(jobs.values_list("pk", flat=True)[:batch_size])
        if not pks:
            break
        total_feedback += AIFeedback.objects.filter(job_id__in=pks).delete()[0]
        total_jobs += len(pks)
        AIJob.objects.filter(pk__in=pks).delete()
    return total_jobs, total_feedback


class Command(BaseCommand):
    help = "Purge expired guest sessions/recordings and stale failed AI jobs."

    def add_arguments(self, parser) -> None:  # noqa: ANN001
        parser.add_argument(
            "--execute",
            action="store_true",
            help="Delete matched rows. Without it the command only reports a dry run.",
        )
        parser.add_argument(
            "--guest-expired-after-hours",
            type=int,
            default=24,
            help=(
                "Remove guest sessions expired at least this many hours ago "
                f"({MIN_GUEST_EXPIRED_HOURS}-{MAX_GUEST_EXPIRED_HOURS})."
            ),
        )
        parser.add_argument(
            "--ai-failed-after-days",
            type=int,
            default=30,
            help=(
                "Remove failed AI jobs completed at least this many days ago "
                f"({MIN_AI_FAILED_DAYS}-{MAX_AI_FAILED_DAYS})."
            ),
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=1000,
            help=(
                f"Rows deleted per transaction ({MIN_BATCH_SIZE}-{MAX_BATCH_SIZE})."
            ),
        )

    def handle(self, *args, **options) -> None:  # noqa: ANN001
        guest_hours = options["guest_expired_after_hours"]
        ai_days = options["ai_failed_after_days"]
        batch_size = options["batch_size"]

        if not MIN_GUEST_EXPIRED_HOURS <= guest_hours <= MAX_GUEST_EXPIRED_HOURS:
            raise CommandError(
                f"--guest-expired-after-hours must be between "
                f"{MIN_GUEST_EXPIRED_HOURS} and {MAX_GUEST_EXPIRED_HOURS}."
            )
        if not MIN_AI_FAILED_DAYS <= ai_days <= MAX_AI_FAILED_DAYS:
            raise CommandError(
                f"--ai-failed-after-days must be between "
                f"{MIN_AI_FAILED_DAYS} and {MAX_AI_FAILED_DAYS}."
            )
        if not MIN_BATCH_SIZE <= batch_size <= MAX_BATCH_SIZE:
            raise CommandError(
                f"--batch-size must be between {MIN_BATCH_SIZE} and {MAX_BATCH_SIZE}."
            )

        now = timezone.now()
        guest_cutoff = now - timedelta(hours=guest_hours)
        ai_cutoff = now - timedelta(days=ai_days)

        guest_sessions = AssessmentSession.objects.filter(
            user__isnull=True, guest_expires_at__lt=guest_cutoff
        )
        failed_jobs = AIJob.objects.filter(
            status=AIJobStatus.FAILED, completed_at__lt=ai_cutoff
        )

        guest_count = guest_sessions.count()
        job_count = failed_jobs.count()

        if not options["execute"]:
            self.stdout.write("[dry-run] Nothing was deleted. Matched:")
            self.stdout.write(
                f"  {guest_count} expired guest session(s) "
                "(their private recordings cascade with them)"
            )
            self.stdout.write(f"  {job_count} stale failed AI job(s)")
            self.stdout.write("Re-run with --execute to delete these rows.")
            return

        sessions_deleted, guest_feedback_deleted = _purge_guest_sessions(
            guest_sessions, batch_size
        )
        jobs_deleted, job_feedback_deleted = _purge_failed_jobs(
            failed_jobs, batch_size
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Deleted {sessions_deleted} guest session(s), "
                f"{guest_feedback_deleted} linked AI feedback row(s), "
                f"{jobs_deleted} stale failed AI job(s), and "
                f"{job_feedback_deleted} linked AI feedback row(s)."
            )
        )
