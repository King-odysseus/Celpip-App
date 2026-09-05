"""Frozen orchestration records for full four-component mock attempts."""

from __future__ import annotations

import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.content.models import ContentVersion, Skill, TestFormatVersion


class MockState(models.TextChoices):
    READY = "ready", "Ready"
    ACTIVE = "active", "Active"
    BETWEEN_SECTIONS = "between_sections", "Between sections"
    COMPLETED = "completed", "Completed"
    ABANDONED = "abandoned", "Abandoned"


class MockTaskState(models.TextChoices):
    PENDING = "pending", "Pending"
    CURRENT = "current", "Current"
    SUBMITTED = "submitted", "Submitted"
    SKIPPED = "skipped", "Skipped"


class MockAttempt(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="mock_attempts"
    )
    format_version = models.ForeignKey(
        TestFormatVersion, on_delete=models.PROTECT, related_name="mock_attempts"
    )
    format_snapshot = models.JSONField()
    scope = models.CharField(max_length=40, default="compact_task_family_mock")
    state = models.CharField(max_length=20, choices=MockState.choices, default=MockState.READY)
    current_order = models.PositiveSmallIntegerField(default=0)
    current_section = models.CharField(max_length=16, choices=Skill.choices, blank=True)
    section_started_at = models.DateTimeField(null=True, blank=True)
    section_deadline_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    scheduled_for = models.DateField(
        null=True,
        blank=True,
        help_text="Learner-selected local date for a full simulation, if scheduled.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    # {section: {"started_at": iso, "ended_at": iso | None}}, one entry per
    # component. section_started_at/section_deadline_at are overwritten as the
    # attempt progresses, so this is the only durable per-section timing
    # record once the attempt completes — the completion review's "time used"
    # has nowhere else to read it from.
    section_log = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "state", "-created_at"])]

    def __str__(self) -> str:
        return f"Mock {self.pk} ({self.state})"


class MockTask(models.Model):
    attempt = models.ForeignKey(MockAttempt, on_delete=models.CASCADE, related_name="tasks")
    order = models.PositiveSmallIntegerField()
    section = models.CharField(max_length=16, choices=Skill.choices)
    task_type = models.CharField(max_length=64)
    content_version = models.ForeignKey(
        ContentVersion, on_delete=models.PROTECT, related_name="mock_tasks"
    )
    session = models.OneToOneField(
        "assessments.AssessmentSession",
        on_delete=models.PROTECT,
        related_name="mock_task",
    )
    snapshot = models.JSONField()
    state = models.CharField(
        max_length=12, choices=MockTaskState.choices, default=MockTaskState.PENDING
    )
    is_simulated_unscored = models.BooleanField(default=False)

    class Meta:
        ordering = ["order"]
        constraints = [
            models.UniqueConstraint(
                fields=["attempt", "order"], name="mocks_unique_attempt_task_order"
            ),
            # The compact mock has exactly one MockTask per task_type. The
            # full-length mock (see mocks.services.OFFICIAL_COUNTS) instead
            # combines several distinct content versions of the same
            # task_type to reach the official question count, so task_type
            # alone can no longer be unique per attempt. Duplicate content is
            # still prevented: the same content_version can never appear
            # twice in one attempt, under any scope.
            models.UniqueConstraint(
                fields=["attempt", "content_version"],
                name="mocks_unique_attempt_content_version",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.attempt_id}: {self.order} {self.task_type}"

    def save(self, *args, **kwargs) -> None:
        if self.pk:
            original = type(self).objects.get(pk=self.pk)
            immutable = (
                "attempt_id",
                "order",
                "section",
                "task_type",
                "content_version_id",
                "session_id",
                "snapshot",
                "is_simulated_unscored",
            )
            if any(getattr(self, field) != getattr(original, field) for field in immutable):
                raise ValidationError("Frozen mock task details are immutable.")
        super().save(*args, **kwargs)
