"""Versioned, original practice content and its editorial metadata."""
from __future__ import annotations

import uuid
from typing import Any

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Skill(models.TextChoices):
    LISTENING = "listening", "Listening"
    READING = "reading", "Reading"
    WRITING = "writing", "Writing"
    SPEAKING = "speaking", "Speaking"


class SourceType(models.TextChoices):
    HUMAN_AUTHORED = "human_authored", "Human authored"
    AI_GENERATED = "ai_generated", "AI-generated draft"


class PublicationStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    IN_REVIEW = "in_review", "In review"
    PUBLISHED = "published", "Published"
    RETIRED = "retired", "Retired"


class TestFormatVersion(models.Model):
    code = models.SlugField(max_length=40, unique=True)
    name = models.CharField(max_length=120)
    is_active = models.BooleanField(default=False)
    verified_on = models.DateField()
    official_source_urls = models.JSONField(default=list)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-verified_on", "code"]

    def __str__(self) -> str:
        return self.name


class TaskType(models.Model):
    """A stable task code whose display guidance can evolve independently."""

    code = models.SlugField(max_length=64, primary_key=True)
    skill = models.CharField(max_length=16, choices=Skill.choices)
    title = models.CharField(max_length=120)
    part_number = models.PositiveSmallIntegerField()
    description = models.TextField()
    strategy = models.JSONField(default=list)
    common_mistakes = models.JSONField(default=list)
    format_versions = models.ManyToManyField(
        TestFormatVersion, related_name="task_types", blank=True
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["skill", "part_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["skill", "part_number"], name="content_unique_skill_part"
            )
        ]

    def __str__(self) -> str:
        return self.title


class ContentItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    slug = models.SlugField(max_length=120, unique=True)
    task_type = models.ForeignKey(
        TaskType, on_delete=models.PROTECT, related_name="content_items"
    )
    title = models.CharField(max_length=180)
    topic = models.CharField(max_length=120)
    difficulty = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(3)]
    )
    estimated_level = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(12)]
    )
    source_type = models.CharField(
        max_length=20, choices=SourceType.choices, default=SourceType.HUMAN_AUTHORED
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="authored_content",
    )
    provenance = models.TextField(
        help_text="How this original material was created and checked."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["task_type__part_number", "slug"]

    def __str__(self) -> str:
        return self.title


class ContentVersion(models.Model):
    item = models.ForeignKey(
        ContentItem, on_delete=models.CASCADE, related_name="versions"
    )
    version = models.PositiveIntegerField()
    status = models.CharField(
        max_length=16, choices=PublicationStatus.choices, default=PublicationStatus.DRAFT
    )
    instructions = models.TextField()
    stimulus = models.JSONField(
        help_text="Structured original email, prose, notice, or table content."
    )
    learning_notes = models.TextField(blank=True)
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reviewed_content_versions",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["item", "-version"]
        constraints = [
            models.UniqueConstraint(
                fields=["item", "version"], name="content_unique_item_version"
            )
        ]

    def __str__(self) -> str:
        return f"{self.item.title} v{self.version} ({self.status})"

    def save(self, *args: Any, **kwargs: Any) -> None:
        if self.pk:
            original = ContentVersion.objects.get(pk=self.pk)
            if original.status in {
                PublicationStatus.PUBLISHED,
                PublicationStatus.RETIRED,
            }:
                raise ValidationError(
                    "Published content is immutable; create a new version instead."
                )
        super().save(*args, **kwargs)

    def delete(self, *args: Any, **kwargs: Any) -> tuple[int, dict[str, int]]:
        if self.status in {PublicationStatus.PUBLISHED, PublicationStatus.RETIRED}:
            raise ValidationError("Published or retired content cannot be deleted.")
        return super().delete(*args, **kwargs)


class SkillFocus(models.TextChoices):
    GIST = "gist", "Gist"
    DETAIL = "detail", "Detail"
    INFERENCE = "inference", "Inference"
    VOCABULARY = "vocabulary", "Vocabulary in context"
    PURPOSE = "purpose", "Purpose"


class Question(models.Model):
    content_version = models.ForeignKey(
        ContentVersion, on_delete=models.CASCADE, related_name="questions"
    )
    order = models.PositiveSmallIntegerField()
    stem = models.TextField()
    skill_focus = models.CharField(max_length=16, choices=SkillFocus.choices)
    evidence = models.TextField()
    explanation = models.TextField()

    class Meta:
        ordering = ["order"]
        constraints = [
            models.UniqueConstraint(
                fields=["content_version", "order"],
                name="content_unique_question_order",
            )
        ]

    def __str__(self) -> str:
        return f"{self.content_version}: question {self.order}"

    def save(self, *args: Any, **kwargs: Any) -> None:
        self._assert_mutable()
        super().save(*args, **kwargs)

    def delete(self, *args: Any, **kwargs: Any) -> tuple[int, dict[str, int]]:
        self._assert_mutable()
        return super().delete(*args, **kwargs)

    def _assert_mutable(self) -> None:
        status = ContentVersion.objects.values_list("status", flat=True).get(
            pk=self.content_version_id
        )
        if status in {
            PublicationStatus.PUBLISHED,
            PublicationStatus.RETIRED,
        }:
            raise ValidationError("Questions on published content are immutable.")


class Choice(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="choices")
    order = models.PositiveSmallIntegerField()
    text = models.TextField()
    is_correct = models.BooleanField(default=False)
    explanation = models.TextField()

    class Meta:
        ordering = ["order"]
        constraints = [
            models.UniqueConstraint(
                fields=["question", "order"], name="content_unique_choice_order"
            )
        ]

    def __str__(self) -> str:
        return f"{self.question} choice {self.order}"

    def save(self, *args: Any, **kwargs: Any) -> None:
        self._assert_mutable()
        super().save(*args, **kwargs)

    def delete(self, *args: Any, **kwargs: Any) -> tuple[int, dict[str, int]]:
        self._assert_mutable()
        return super().delete(*args, **kwargs)

    def _assert_mutable(self) -> None:
        status = ContentVersion.objects.values_list("status", flat=True).get(
            pk=self.question.content_version_id
        )
        if status in {
            PublicationStatus.PUBLISHED,
            PublicationStatus.RETIRED,
        }:
            raise ValidationError("Choices on published content are immutable.")
