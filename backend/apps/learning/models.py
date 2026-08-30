from __future__ import annotations

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from apps.content.models import Question, Skill, TaskType


class MistakeState(models.TextChoices):
    OPEN = "open", "Open"
    RESOLVED = "resolved", "Resolved"


class MistakeRecord(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="mistakes"
    )
    question = models.ForeignKey(
        Question, on_delete=models.PROTECT, related_name="learner_mistakes"
    )
    skill = models.CharField(max_length=16, choices=Skill.choices)
    task_type = models.ForeignKey(
        TaskType, on_delete=models.PROTECT, related_name="learner_mistakes"
    )
    stem_snapshot = models.TextField()
    selected_snapshot = models.TextField(blank=True)
    correct_snapshot = models.TextField()
    explanation_snapshot = models.TextField()
    occurrences = models.PositiveIntegerField(default=1)
    state = models.CharField(max_length=12, choices=MistakeState.choices, default=MistakeState.OPEN)
    first_seen_at = models.DateTimeField()
    last_seen_at = models.DateTimeField()
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-occurrences", "-last_seen_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "question"], name="learning_unique_user_question_mistake"
            )
        ]
        indexes = [models.Index(fields=["user", "state", "-last_seen_at"])]

    def __str__(self) -> str:
        return f"{self.user_id}: {self.task_type_id} question {self.question_id}"


class StudyPlan(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="study_plans"
    )
    version = models.PositiveIntegerField()
    is_active = models.BooleanField(default=True)
    reason_summary = models.JSONField(default=dict)
    generated_at = models.DateTimeField(auto_now_add=True)
    # Learner-chosen plan name; carried across regenerations so it never resets.
    name = models.CharField(max_length=120, blank=True, default="")

    class Meta:
        ordering = ["-version"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "version"], name="learning_unique_user_plan_version"
            ),
            models.UniqueConstraint(
                fields=["user"],
                condition=Q(is_active=True),
                name="learning_one_active_plan_per_user",
            ),
        ]

    def __str__(self) -> str:
        return f"Study plan v{self.version} for {self.user_id}"


class StudyTaskState(models.TextChoices):
    PENDING = "pending", "Pending"
    COMPLETED = "completed", "Completed"
    SKIPPED = "skipped", "Skipped"


class StudyTask(models.Model):
    plan = models.ForeignKey(StudyPlan, on_delete=models.CASCADE, related_name="tasks")
    scheduled_date = models.DateField()
    order = models.PositiveSmallIntegerField()
    skill = models.CharField(max_length=16, choices=Skill.choices)
    task_type = models.ForeignKey(TaskType, on_delete=models.PROTECT, related_name="planned_tasks")
    title = models.CharField(max_length=180)
    minutes = models.PositiveSmallIntegerField()
    reason = models.TextField()
    destination = models.CharField(max_length=180)
    state = models.CharField(
        max_length=12, choices=StudyTaskState.choices, default=StudyTaskState.PENDING
    )
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["scheduled_date", "order"]
        constraints = [
            models.UniqueConstraint(
                fields=["plan", "scheduled_date", "order"],
                name="learning_unique_plan_day_order",
            )
        ]

    def __str__(self) -> str:
        return f"{self.scheduled_date}: {self.title}"

    def save(self, *args, **kwargs) -> None:
        if self.pk:
            original = type(self).objects.get(pk=self.pk)
            immutable = (
                "plan_id",
                "scheduled_date",
                "order",
                "skill",
                "task_type_id",
                "title",
                "minutes",
                "reason",
                "destination",
            )
            if any(getattr(original, field) != getattr(self, field) for field in immutable):
                raise ValidationError("Generated study task details are immutable.")
        super().save(*args, **kwargs)
