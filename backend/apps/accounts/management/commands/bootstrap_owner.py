"""Create (or update) the single owner account and its learner profile.

The default exam date lives here as a command default only — it is passed in as
an option and never referenced as a global constant elsewhere in the codebase,
so the product is not hard-coded to one learner's test date.
"""
from __future__ import annotations

import datetime as dt
import os

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.accounts import services
from apps.accounts.models import LearnerProfile, User

# The owner in the plan sits the exam on this date; supplied as a default the
# operator can override with --exam-date. Not imported anywhere else.
DEFAULT_OWNER_EXAM_DATE = "2026-10-10"
DEFAULT_TARGET_LEVEL = 9


class Command(BaseCommand):
    help = "Create or update the owner account, profile, and recovery code."

    def add_arguments(self, parser) -> None:  # noqa: ANN001
        parser.add_argument("--identifier", required=True)
        parser.add_argument(
            "--password",
            default=None,
            help="Owner password. Falls back to the OWNER_PASSWORD env var.",
        )
        parser.add_argument(
            "--exam-date",
            default=DEFAULT_OWNER_EXAM_DATE,
            help=f"ISO exam date (YYYY-MM-DD). Defaults to {DEFAULT_OWNER_EXAM_DATE}.",
        )
        parser.add_argument(
            "--target-level", type=int, default=DEFAULT_TARGET_LEVEL
        )
        parser.add_argument("--staff", action="store_true", help="Grant staff access.")

    @transaction.atomic
    def handle(self, *args, **options) -> None:
        identifier = options["identifier"]
        password = options["password"] or os.environ.get("OWNER_PASSWORD")
        if not password:
            raise CommandError(
                "Provide --password or set the OWNER_PASSWORD environment variable."
            )
        try:
            exam_date = dt.date.fromisoformat(options["exam_date"])
        except ValueError as exc:
            raise CommandError("--exam-date must be YYYY-MM-DD.") from exc

        target_level = options["target_level"]
        normalized = User.objects.normalize_identifier(identifier)
        existing = User.objects.filter(identifier=normalized).first()

        if existing is None:
            try:
                result = services.register_user(identifier, password)
            except services.AccountError as exc:
                raise CommandError(str(exc)) from exc
            user = result.user
            recovery_code = result.recovery_code
            self.stdout.write(self.style.SUCCESS(f"Created owner '{user.identifier}'."))
        else:
            services.validate_password(password)
            user = existing
            user.set_password(password)
            user.save(update_fields=["password"])
            recovery_code = services.issue_recovery_code(user)
            self.stdout.write(
                self.style.WARNING(
                    f"Owner '{user.identifier}' already existed; password and "
                    "recovery code were reset."
                )
            )

        if options["staff"]:
            user.is_staff = True
            user.save(update_fields=["is_staff"])

        LearnerProfile.objects.update_or_create(
            user=user,
            defaults={"exam_date": exam_date, "target_level": target_level},
        )

        self.stdout.write(f"Exam date set to {exam_date.isoformat()}.")
        self.stdout.write(
            self.style.NOTICE(
                "Recovery code (shown once — store it securely):\n"
                f"    {recovery_code}"
            )
        )
