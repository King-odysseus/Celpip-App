from __future__ import annotations

from collections import defaultdict
from datetime import timedelta
from itertools import cycle
from zoneinfo import ZoneInfo

from django.db import transaction
from django.db.models import Count
from django.http import Http404
from django.utils import timezone

from apps.accounts.models import LearnerProfile
from apps.ai_services.models import AIFeedback
from apps.assessments.models import ObjectiveResult
from apps.content.models import Question, Skill, TaskType

from .models import (
    MistakeRecord,
    MistakeState,
    StudyPlan,
    StudyTask,
    StudyTaskState,
)

SKILLS = (Skill.LISTENING, Skill.READING, Skill.WRITING, Skill.SPEAKING)
SKILL_LABELS = dict(Skill.choices)


def _profile_for(user):
    profile, _ = LearnerProfile.objects.get_or_create(user=user)
    return profile


def progress_payload(user) -> dict:
    profile = _profile_for(user)
    objective = list(
        ObjectiveResult.objects.filter(session__user=user)
        .select_related("session")
        .order_by("scored_at")
    )
    feedback = list(
        AIFeedback.objects.filter(session_item__session__user=user)
        .select_related("session_item__session")
        .order_by("created_at")
    )
    by_skill: dict[str, dict] = {
        skill: {
            "skill": skill,
            "attempts": 0,
            "questions_correct": 0,
            "questions_total": 0,
            "accuracy_percent": None,
            "estimate_low": None,
            "estimate_high": None,
            "target": profile.target_for(skill),
            "last_activity": None,
        }
        for skill in SKILLS
    }
    trends = []
    task_stats: dict[str, dict] = {}
    for result in objective:
        item = result.session.items.get()
        skill = item.snapshot["skill"]
        summary = by_skill[skill]
        summary["attempts"] += 1
        summary["questions_correct"] += result.raw_correct
        summary["questions_total"] += result.raw_possible
        summary["last_activity"] = result.scored_at
        task_code = item.snapshot["task_type"]
        stat = task_stats.setdefault(
            task_code,
            {
                "task_type": task_code,
                "skill": skill,
                "title": item.snapshot.get("title", task_code),
                "correct": 0,
                "total": 0,
            },
        )
        stat["correct"] += result.raw_correct
        stat["total"] += result.raw_possible
        trends.append(
            {
                "date": result.scored_at,
                "skill": skill,
                "metric": "accuracy_percent",
                "value": round(100 * result.raw_correct / result.raw_possible),
                "label": "Practice accuracy",
            }
        )
    feedback_ranges: dict[str, list[tuple[int, int]]] = defaultdict(list)
    for artifact in feedback:
        skill = artifact.session_item.snapshot["skill"]
        assessment = artifact.assessment
        low, high = assessment["estimated_level_low"], assessment["estimated_level_high"]
        feedback_ranges[skill].append((low, high))
        summary = by_skill[skill]
        summary["attempts"] += 1
        summary["last_activity"] = artifact.created_at
        trends.append(
            {
                "date": artifact.created_at,
                "skill": skill,
                "metric": "estimated_midpoint",
                "value": round((low + high) / 2, 1),
                "label": "AI-assisted practice estimate",
            }
        )
    for skill, summary in by_skill.items():
        total = summary["questions_total"]
        if total:
            summary["accuracy_percent"] = round(100 * summary["questions_correct"] / total)
        ranges = feedback_ranges.get(skill, [])[-5:]
        if ranges:
            summary["estimate_low"] = round(sum(low for low, _ in ranges) / len(ranges), 1)
            summary["estimate_high"] = round(sum(high for _, high in ranges) / len(ranges), 1)
    for stat in task_stats.values():
        stat["accuracy_percent"] = round(100 * stat["correct"] / stat["total"])

    practiced = sum(summary["attempts"] > 0 for summary in by_skill.values())
    return {
        "skills": list(by_skill.values()),
        "task_types": sorted(task_stats.values(), key=lambda value: value["accuracy_percent"]),
        "trends": sorted(trends, key=lambda value: value["date"]),
        "coverage": {"practised_skills": practiced, "total_skills": 4},
        "overall_readiness": None,
        "readiness_explanation": (
            "A single overall readiness number is withheld. CELPIP reports four component "
            "levels, and the platform keeps objective accuracy separate from AI-assisted estimates."
        ),
        "disclaimer": "Practice analytics are not official CELPIP results.",
    }


@transaction.atomic
def record_objective_learning(result: ObjectiveResult) -> None:
    if result.session.user_id is None:
        return
    item = result.session.items.get()
    questions = {
        question.pk: question
        for question in Question.objects.filter(
            content_version=item.content_version
        ).prefetch_related("choices")
    }
    for outcome in result.outcomes:
        question = questions[outcome["question_id"]]
        existing = MistakeRecord.objects.filter(
            user_id=result.session.user_id, question=question
        ).first()
        if outcome["is_correct"]:
            if existing and existing.state == MistakeState.OPEN:
                existing.state = MistakeState.RESOLVED
                existing.resolved_at = result.scored_at
                existing.save(update_fields=["state", "resolved_at"])
            continue
        choices = {choice.pk: choice for choice in question.choices.all()}
        selected = choices.get(outcome["selected_choice_id"])
        correct = choices[outcome["correct_choice_id"]]
        defaults = {
            "skill": item.snapshot["skill"],
            "task_type_id": item.snapshot["task_type"],
            "stem_snapshot": question.stem,
            "selected_snapshot": selected.text if selected else "No answer selected",
            "correct_snapshot": correct.text,
            "explanation_snapshot": question.explanation,
            "first_seen_at": result.scored_at,
            "last_seen_at": result.scored_at,
        }
        if existing:
            for key, value in defaults.items():
                if key != "first_seen_at":
                    setattr(existing, key, value)
            existing.occurrences += 1
            existing.state = MistakeState.OPEN
            existing.resolved_at = None
            existing.save()
        else:
            MistakeRecord.objects.create(
                user_id=result.session.user_id,
                question=question,
                **defaults,
            )
    regenerate_plan(result.session.user)


def _skill_priority(progress: dict) -> dict[str, float]:
    priorities = {}
    for summary in progress["skills"]:
        if summary["attempts"] == 0:
            priority = 120
        elif summary["accuracy_percent"] is not None:
            priority = 100 - summary["accuracy_percent"]
        elif summary["estimate_low"] is not None:
            midpoint = (summary["estimate_low"] + summary["estimate_high"]) / 2
            priority = max(5, (summary["target"] - midpoint) * 12)
        else:
            priority = 80
        priorities[summary["skill"]] = round(priority, 1)
    return priorities


@transaction.atomic
def regenerate_plan(user) -> StudyPlan:
    profile = _profile_for(user)
    progress = progress_payload(user)
    priorities = _skill_priority(progress)
    previous = StudyPlan.objects.filter(user=user, is_active=True).first()
    version = (
        StudyPlan.objects.filter(user=user)
        .order_by("-version")
        .values_list("version", flat=True)
        .first()
        or 0
    ) + 1
    if previous:
        previous.is_active = False
        previous.save(update_fields=["is_active"])
    plan = StudyPlan.objects.create(
        user=user,
        version=version,
        reason_summary={
            "priorities": priorities,
            "rule": "Unpractised and weaker skills come first; every skill remains in rotation.",
            "source_attempts": sum(item["attempts"] for item in progress["skills"]),
        },
    )
    mistakes = {
        row["skill"]: row["count"]
        for row in MistakeRecord.objects.filter(user=user, state=MistakeState.OPEN)
        .values("skill")
        .annotate(count=Count("id"))
    }
    task_types = {
        skill: list(TaskType.objects.filter(skill=skill, is_active=True).order_by("part_number"))
        for skill in SKILLS
    }
    ranked = sorted(
        (skill for skill in SKILLS if task_types[skill]),
        key=lambda skill: (-priorities[skill], skill),
    )
    if not ranked:
        return plan
    rotation = cycle(ranked + ranked[:2])
    local_today = timezone.now().astimezone(ZoneInfo(profile.timezone)).date()
    preferred = set(profile.preferred_weekdays or range(1, 8))
    study_dates = []
    cursor = local_today
    end = min(
        local_today + timedelta(days=13),
        profile.exam_date
        if profile.exam_date and profile.exam_date >= local_today
        else local_today + timedelta(days=13),
    )
    while cursor <= end:
        if cursor.isoweekday() in preferred:
            study_dates.append(cursor)
        cursor += timedelta(days=1)
    if not study_dates:
        study_dates = [local_today]
    tasks_per_day = max(1, min(3, profile.daily_minutes // 15))
    minutes = max(5, profile.daily_minutes // tasks_per_day)
    type_offsets = defaultdict(int)
    for scheduled_date in study_dates:
        for order in range(1, tasks_per_day + 1):
            skill = next(rotation)
            choices = task_types[skill]
            task_type = choices[type_offsets[skill] % len(choices)]
            type_offsets[skill] += 1
            mistake_count = mistakes.get(skill, 0)
            reason = f"{SKILL_LABELS[skill]} priority {priorities[skill]:g}. " + (
                f"You have {mistake_count} open mistake pattern(s)."
                if mistake_count
                else "This keeps all four skills in rotation."
            )
            destination = {
                Skill.READING: "/practice",
                Skill.LISTENING: "/practice/listening",
                Skill.WRITING: "/practice/writing",
                Skill.SPEAKING: "/practice/speaking",
            }[skill]
            StudyTask.objects.create(
                plan=plan,
                scheduled_date=scheduled_date,
                order=order,
                skill=skill,
                task_type=task_type,
                title=f"Practise {task_type.title}",
                minutes=minutes,
                reason=reason,
                destination=destination,
            )
    return plan


def plan_payload(plan: StudyPlan) -> dict:
    return {
        "id": plan.pk,
        "version": plan.version,
        "generated_at": plan.generated_at,
        "reason_summary": plan.reason_summary,
        "tasks": [
            {
                "id": task.pk,
                "scheduled_date": task.scheduled_date,
                "order": task.order,
                "skill": task.skill,
                "task_type": task.task_type_id,
                "title": task.title,
                "minutes": task.minutes,
                "reason": task.reason,
                "destination": task.destination,
                "state": task.state,
                "completed_at": task.completed_at,
            }
            for task in plan.tasks.select_related("task_type")
        ],
    }


@transaction.atomic
def set_task_state(*, user, task_id: int, state: str) -> StudyTask:
    try:
        task = StudyTask.objects.select_for_update().get(
            pk=task_id, plan__user=user, plan__is_active=True
        )
    except StudyTask.DoesNotExist as exc:
        raise Http404 from exc
    task.state = state
    task.completed_at = timezone.now() if state == StudyTaskState.COMPLETED else None
    task.save(update_fields=["state", "completed_at"])
    return task
