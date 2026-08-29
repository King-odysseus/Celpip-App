"""Auditable queue records and immutable model-assisted feedback."""

from __future__ import annotations

import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q


class AIJobKind(models.TextChoices):
    WRITING_FEEDBACK = "writing_feedback", "Writing feedback"
    SPEAKING_FEEDBACK = "speaking_feedback", "Speaking feedback"
    CONTENT_DRAFT = "content_draft", "Content draft"
    IMAGE_DRAFT = "image_draft", "Image draft"
    SPEECH_DRAFT = "speech_draft", "Speech draft"


class AIJobStatus(models.TextChoices):
    QUEUED = "queued", "Queued"
    RUNNING = "running", "Running"
    SUCCEEDED = "succeeded", "Succeeded"
    FAILED = "failed", "Failed"


class AIJob(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    kind = models.CharField(max_length=24, choices=AIJobKind.choices)
    status = models.CharField(
        max_length=12, choices=AIJobStatus.choices, default=AIJobStatus.QUEUED
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="ai_jobs",
    )
    session_item = models.ForeignKey(
        "assessments.SessionItem",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="ai_jobs",
    )
    content_version = models.ForeignKey(
        "content.ContentVersion",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="ai_jobs",
    )
    provider = models.CharField(max_length=32)
    model = models.CharField(max_length=80)
    prompt_version = models.CharField(max_length=40)
    schema_version = models.CharField(max_length=20, default="1")
    input_snapshot = models.JSONField(default=dict)
    output = models.JSONField(default=dict, blank=True)
    external_id = models.CharField(max_length=120, blank=True)
    usage = models.JSONField(default=dict, blank=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    max_attempts = models.PositiveSmallIntegerField(default=3)
    run_after = models.DateTimeField()
    locked_at = models.DateTimeField(null=True, blank=True)
    error_code = models.CharField(max_length=80, blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["status", "run_after", "created_at"]),
            models.Index(fields=["session_item", "kind", "-created_at"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(session_item__isnull=False)
                    | Q(content_version__isnull=False)
                    | Q(kind=AIJobKind.CONTENT_DRAFT)
                ),
                name="ai_job_has_subject",
            )
        ]

    def __str__(self) -> str:
        return f"{self.get_kind_display()} ({self.status})"


class AIFeedback(models.Model):
    """One final, immutable AI-assisted feedback artifact per session item."""

    session_item = models.OneToOneField(
        "assessments.SessionItem",
        on_delete=models.CASCADE,
        related_name="ai_feedback",
    )
    job = models.OneToOneField(AIJob, on_delete=models.PROTECT, related_name="feedback")
    kind = models.CharField(
        max_length=24,
        choices=(
            (AIJobKind.WRITING_FEEDBACK, "Writing feedback"),
            (AIJobKind.SPEAKING_FEEDBACK, "Speaking feedback"),
        ),
    )
    provider = models.CharField(max_length=32)
    model = models.CharField(max_length=80)
    prompt_version = models.CharField(max_length=40)
    transcript = models.TextField(blank=True)
    assessment = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"AI feedback for {self.session_item_id}"

    def save(self, *args, **kwargs) -> None:
        if self.pk:
            raise ValidationError("AI feedback is immutable; create a new versioned artifact.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("AI feedback is an immutable audit record.")
