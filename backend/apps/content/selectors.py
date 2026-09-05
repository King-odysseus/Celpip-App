from django.db.models import Prefetch, QuerySet

from .models import Choice, ContentVersion, PublicationStatus, Question, TaskType


def active_task_types(skill: str) -> QuerySet[TaskType]:
    return TaskType.objects.filter(skill=skill, is_active=True).order_by("part_number")


def published_versions(skill: str) -> QuerySet[ContentVersion]:
    questions = Question.objects.order_by("order").prefetch_related(
        Prefetch("choices", queryset=Choice.objects.order_by("order"))
    )
    return (
        ContentVersion.objects.filter(
            status=PublicationStatus.PUBLISHED,
            item__task_type__skill=skill,
            item__task_type__is_active=True,
        )
        .exclude(quality_reports__status="confirmed")
        .select_related("item", "item__task_type")
        .prefetch_related(Prefetch("questions", queryset=questions))
        .order_by("item__task_type__part_number", "item__difficulty", "item__slug")
    )
