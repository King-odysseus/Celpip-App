"""Frozen assessment sessions and revision-safe objective responses."""
from __future__ import annotations

import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from apps.content.models import Choice, ContentVersion, Question


class SessionMode(models.TextChoices):
    LEARN = "learn", "Learn"
    PRACTICE = "practice", "Practice"


class SessionState(models.TextChoices):
    ACTIVE = "active", "Active"
    SUBMITTED = "submitted", "Submitted"


class AssessmentSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="assessment_sessions",
    )
    guest_token_hash = models.CharField(max_length=64, blank=True, editable=False)
    guest_expires_at = models.DateTimeField(null=True, blank=True, editable=False)
    mode = models.CharField(max_length=12, choices=SessionMode.choices)
    state = models.CharField(
        max_length=12, choices=SessionState.choices, default=SessionState.ACTIVE
    )
    started_at = models.DateTimeField(auto_now_add=True)
    deadline_at = models.DateTimeField(null=True, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    last_activity_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-started_at"]
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(user__isnull=False)
                    | (~Q(guest_token_hash="") & Q(guest_expires_at__isnull=False))
                ),
                name="assessments_session_has_owner",
            ),
            models.CheckConstraint(
                condition=Q(mode=SessionMode.PRACTICE) | Q(deadline_at__isnull=True),
                name="assessments_only_practice_has_deadline",
            ),
        ]
        indexes = [
            models.Index(fields=["user", "state", "-started_at"]),
            models.Index(fields=["state", "deadline_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.get_mode_display()} session {self.pk}"


class SessionItem(models.Model):
    session = models.ForeignKey(
        AssessmentSession, on_delete=models.CASCADE, related_name="items"
    )
    content_version = models.ForeignKey(
        ContentVersion, on_delete=models.PROTECT, related_name="session_items"
    )
    order = models.PositiveSmallIntegerField()
    snapshot = models.JSONField()

    class Meta:
        ordering = ["order"]
        constraints = [
            models.UniqueConstraint(
                fields=["session", "order"], name="assessments_unique_session_item_order"
            ),
            models.UniqueConstraint(
                fields=["session", "content_version"],
                name="assessments_unique_session_content",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.session_id}: item {self.order}"


class Response(models.Model):
    session_item = models.ForeignKey(
        SessionItem, on_delete=models.CASCADE, related_name="responses"
    )
    question = models.ForeignKey(
        Question, on_delete=models.PROTECT, related_name="assessment_responses"
    )
    selected_choice = models.ForeignKey(
        Choice,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="assessment_responses",
    )
    revision = models.PositiveIntegerField(default=0)
    last_idempotency_key = models.UUIDField(null=True, blank=True)
    last_payload_hash = models.CharField(max_length=64, blank=True)
    saved_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["question__order"]
        constraints = [
            models.UniqueConstraint(
                fields=["session_item", "question"],
                name="assessments_unique_item_question_response",
            )
        ]

    def __str__(self) -> str:
        return f"{self.session_item_id}: response to {self.question_id}"

    def clean(self) -> None:
        if self.question.content_version_id != self.session_item.content_version_id:
            raise ValidationError("Question does not belong to the frozen content version.")
        if self.selected_choice_id and self.selected_choice.question_id != self.question_id:
            raise ValidationError("Choice does not belong to the response question.")


class WritingSubmission(models.Model):
    """A learner's constructed writing response for a single frozen prompt.

    One submission per :class:`SessionItem`. Autosave bumps ``revision``
    monotonically; ``last_idempotency_key`` and ``last_payload_hash`` make a
    repeated autosave a safe replay. Once ``submitted_at`` is set the response
    is frozen and may never change.
    """

    session_item = models.OneToOneField(
        SessionItem, on_delete=models.CASCADE, related_name="writing_submission"
    )
    text = models.TextField(blank=True)
    word_count = models.PositiveIntegerField(default=0)
    revision = models.PositiveIntegerField(default=0)
    last_idempotency_key = models.UUIDField(null=True, blank=True)
    last_payload_hash = models.CharField(max_length=64, blank=True)
    saved_at = models.DateTimeField(auto_now=True)
    submitted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        return f"Writing submission for {self.session_item_id}"

    def save(self, *args, **kwargs) -> None:
        """Reject direct model writes after the response has been submitted.

        The service layer already serializes normal writes, but this guard also
        protects against accidental admin, shell, or future code-path edits.
        """
        if self.pk and type(self).objects.filter(pk=self.pk, submitted_at__isnull=False).exists():
            raise ValidationError("A submitted writing response is immutable.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.pk and type(self).objects.filter(pk=self.pk, submitted_at__isnull=False).exists():
            raise ValidationError("A submitted writing response is immutable.")
        return super().delete(*args, **kwargs)

    @property
    def is_submitted(self) -> bool:
        return self.submitted_at is not None


class ObjectiveResult(models.Model):
    session = models.OneToOneField(
        AssessmentSession, on_delete=models.CASCADE, related_name="objective_result"
    )
    raw_correct = models.PositiveIntegerField()
    raw_possible = models.PositiveIntegerField()
    outcomes = models.JSONField(default=list)
    scored_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.raw_correct}/{self.raw_possible} for {self.session_id}"
