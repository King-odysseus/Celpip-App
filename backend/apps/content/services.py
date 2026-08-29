"""Transactional editorial operations and content validation."""
from __future__ import annotations

from dataclasses import dataclass

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from .models import ContentVersion, PublicationStatus, SourceType


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    message: str


def validate_content_version(version: ContentVersion) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    if not version.instructions.strip():
        issues.append(ValidationIssue("missing_instructions", "Instructions are required."))
    if not isinstance(version.stimulus, dict) or not version.stimulus:
        issues.append(ValidationIssue("missing_stimulus", "A structured stimulus is required."))
    if not version.item.provenance.strip():
        issues.append(
            ValidationIssue("missing_provenance", "Original-content provenance is required.")
        )

    questions = list(version.questions.prefetch_related("choices"))
    if not questions:
        issues.append(ValidationIssue("missing_questions", "At least one question is required."))
    for question in questions:
        choices = list(question.choices.all())
        if len(choices) < 2:
            issues.append(
                ValidationIssue(
                    "too_few_choices",
                    f"Question {question.order} needs at least two choices.",
                )
            )
        if sum(choice.is_correct for choice in choices) != 1:
            issues.append(
                ValidationIssue(
                    "invalid_answer_key",
                    f"Question {question.order} needs exactly one correct choice.",
                )
            )
        if not question.explanation.strip() or not question.evidence.strip():
            issues.append(
                ValidationIssue(
                    "missing_feedback",
                    f"Question {question.order} needs evidence and explanation.",
                )
            )
        if any(not choice.explanation.strip() for choice in choices):
            issues.append(
                ValidationIssue(
                    "missing_choice_feedback",
                    f"Question {question.order} has unexplained choices.",
                )
            )
    return issues


@transaction.atomic
def submit_for_review(version: ContentVersion) -> ContentVersion:
    version = ContentVersion.objects.select_for_update().get(pk=version.pk)
    if version.status != PublicationStatus.DRAFT:
        raise ValidationError("Only draft content can be submitted for review.")
    version.status = PublicationStatus.IN_REVIEW
    version.save(update_fields=["status"])
    return version


@transaction.atomic
def return_to_draft(version: ContentVersion) -> ContentVersion:
    version = ContentVersion.objects.select_for_update().get(pk=version.pk)
    if version.status != PublicationStatus.IN_REVIEW:
        raise ValidationError("Only in-review content can return to draft.")
    version.status = PublicationStatus.DRAFT
    version.reviewer = None
    version.reviewed_at = None
    version.save(update_fields=["status", "reviewer", "reviewed_at"])
    return version


@transaction.atomic
def publish(version: ContentVersion, *, reviewer) -> ContentVersion:
    version = ContentVersion.objects.select_for_update().select_related("item").get(pk=version.pk)
    if version.status != PublicationStatus.IN_REVIEW:
        raise ValidationError("Only in-review content can be published.")
    if not reviewer or not reviewer.is_active or not reviewer.is_staff:
        raise ValidationError("An active human staff reviewer must publish content.")
    if version.item.source_type == SourceType.AI_GENERATED and reviewer == version.item.author:
        raise ValidationError("AI drafts require independent human review.")
    issues = validate_content_version(version)
    if issues:
        raise ValidationError({issue.code: issue.message for issue in issues})
    now = timezone.now()
    version.status = PublicationStatus.PUBLISHED
    version.reviewer = reviewer
    version.reviewed_at = now
    version.published_at = now
    version.save(update_fields=["status", "reviewer", "reviewed_at", "published_at"])
    return version


@transaction.atomic
def retire(version: ContentVersion) -> ContentVersion:
    locked = ContentVersion.objects.select_for_update().get(pk=version.pk)
    if locked.status != PublicationStatus.PUBLISHED:
        raise ValidationError("Only published content can be retired.")
    ContentVersion.objects.filter(pk=locked.pk).update(status=PublicationStatus.RETIRED)
    locked.status = PublicationStatus.RETIRED
    return locked
