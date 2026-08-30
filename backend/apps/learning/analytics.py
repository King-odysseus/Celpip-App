"""Authenticated progress analytics and a personalised next-activity suggestion.

Read-only selectors built on already-stored evidence (objective results, AI
feedback, writing/speaking submissions, and mistake records). No schema changes.
The recommendation never fabricates an official CELPIP score: it surfaces the
weakest skill, a target difficulty derived from that skill's own performance,
and a published prompt from the selected task family.
"""
from __future__ import annotations

from django.db.models import Count

from apps.ai_services.models import AIFeedback
from apps.assessments.models import ObjectiveResult, SpeakingSubmission, WritingSubmission
from apps.content.models import ContentVersion, PublicationStatus, TaskType

from .models import MistakeRecord, MistakeState
from .services import (
    RECENT_RESULTS_LIMIT,
    SKILL_LABELS,
    DESTINATIONS,
    _skill_priority,
    progress_payload,
)

HISTORY_PAGE_SIZE_DEFAULT = 20
HISTORY_PAGE_SIZE_MAX = 100

ANALYTICS_DISCLAIMER = "Practice analytics are not official CELPIP results."
RECOMMENDATION_DISCLAIMER = (
    "A personalised practice suggestion, not an official CELPIP score or a requirement."
)


def _objective_entries(user) -> list[dict]:
    entries = []
    results = (
        ObjectiveResult.objects.filter(session__user=user)
        .select_related("session")
        .prefetch_related("session__items")
    )
    for result in results:
        item = result.session.items.first()
        snapshot = item.snapshot if item else {}
        value = (
            round(100 * result.raw_correct / result.raw_possible)
            if result.raw_possible
            else None
        )
        entries.append(
            {
                "id": str(result.session_id),
                "kind": "objective",
                "skill": snapshot.get("skill"),
                "task_type": snapshot.get("task_type"),
                "title": snapshot.get("title", snapshot.get("task_type", "")),
                "date": result.scored_at,
                "measure": "accuracy_percent",
                "value": value,
                "label": "Practice accuracy",
                "destination": DESTINATIONS.get(snapshot.get("skill"), "/practice"),
            }
        )
    return entries


def _constructed_entries(user) -> list[dict]:
    """Writing/speaking submissions, newest activity included even pre-analysis."""
    feedback_map = {
        artifact.session_item_id: artifact
        for artifact in AIFeedback.objects.filter(session_item__session__user=user)
    }
    entries = []
    for model, kind in ((WritingSubmission, "writing"), (SpeakingSubmission, "speaking")):
        rows = (
            model.objects.filter(
                session_item__session__user=user, submitted_at__isnull=False
            )
            .select_related("session_item__session")
        )
        for submission in rows:
            session = submission.session_item.session
            snapshot = submission.session_item.snapshot
            artifact = feedback_map.get(submission.session_item_id)
            if artifact is not None:
                assessment = artifact.assessment
                low = assessment["estimated_level_low"]
                high = assessment["estimated_level_high"]
                entries.append(
                    {
                        "id": str(session.id),
                        "kind": kind,
                        "skill": snapshot.get("skill"),
                        "task_type": snapshot.get("task_type"),
                        "title": snapshot.get("title", snapshot.get("task_type", "")),
                        "date": submission.submitted_at,
                        "measure": "estimated_midpoint",
                        "value": round((low + high) / 2, 1),
                        "label": "AI-assisted practice estimate",
                        "destination": DESTINATIONS.get(snapshot.get("skill"), "/practice"),
                    }
                )
            else:
                entries.append(
                    {
                        "id": str(session.id),
                        "kind": kind,
                        "skill": snapshot.get("skill"),
                        "task_type": snapshot.get("task_type"),
                        "title": snapshot.get("title", snapshot.get("task_type", "")),
                        "date": submission.submitted_at,
                        "measure": "awaiting_feedback",
                        "value": None,
                        "label": "Awaiting AI analysis",
                        "destination": DESTINATIONS.get(snapshot.get("skill"), "/practice"),
                    }
                )
    return entries


def history_payload(user, *, page: int = 1, page_size: int = HISTORY_PAGE_SIZE_DEFAULT) -> dict:
    """Paginated completion history across all four skills, newest first."""
    page_size = max(1, min(page_size, HISTORY_PAGE_SIZE_MAX))
    entries = _objective_entries(user) + _constructed_entries(user)
    entries.sort(key=lambda entry: entry["date"], reverse=True)
    count = len(entries)
    start = (page - 1) * page_size
    page_entries = entries[start : start + page_size]
    return {
        "count": count,
        "page": page,
        "page_size": page_size,
        "results": [{**entry, "date": entry["date"].isoformat()} for entry in page_entries],
        "disclaimer": ANALYTICS_DISCLAIMER,
    }


def analytics_payload(user) -> dict:
    """Aggregate scores, trends, and mistake overview for the analytics view."""
    progress = progress_payload(user)
    open_mistakes = list(
        MistakeRecord.objects.filter(user=user, state=MistakeState.OPEN)
        .select_related("task_type")
    )
    by_skill: dict[str, dict] = {}
    by_task: dict[str, dict] = {}
    for mistake in open_mistakes:
        skill_bucket = by_skill.setdefault(
            mistake.skill, {"skill": mistake.skill, "open": 0, "occurrences": 0}
        )
        skill_bucket["open"] += 1
        skill_bucket["occurrences"] += mistake.occurrences
        task_bucket = by_task.setdefault(
            mistake.task_type_id,
            {
                "task_type": mistake.task_type_id,
                "skill": mistake.skill,
                "title": mistake.task_type.title,
                "open": 0,
                "occurrences": 0,
            },
        )
        task_bucket["open"] += 1
        task_bucket["occurrences"] += mistake.occurrences
    return {
        "skills": progress["skills"],
        "task_types": progress["task_types"],
        "trends": progress["trends"],
        "mistakes": {
            "open_total": len(open_mistakes),
            "by_skill": sorted(by_skill.values(), key=lambda value: -value["occurrences"]),
            "by_task": sorted(by_task.values(), key=lambda value: -value["occurrences"]),
        },
        "history": history_payload(user, page=1, page_size=RECENT_RESULTS_LIMIT)["results"],
        "disclaimer": ANALYTICS_DISCLAIMER,
    }


def _recommended_difficulty(summary: dict) -> int:
    """Map a skill's own performance onto the 1-3 difficulty bank.

    Objective accuracy is the primary signal; AI-assisted estimates fall back to
    the midpoint (1-12 scale). Unpractised skills start on the easier bank so a
    first attempt is approachable rather than overwhelming.
    """
    if summary["accuracy_percent"] is not None:
        accuracy = summary["accuracy_percent"]
        if accuracy >= 80:
            return 3
        if accuracy >= 55:
            return 2
        return 1
    if summary["estimate_low"] is not None:
        midpoint = (summary["estimate_low"] + summary["estimate_high"]) / 2
        if midpoint >= 8:
            return 3
        if midpoint >= 5:
            return 2
        return 1
    return 1


def _published_for(task_type: TaskType, difficulty: int | None) -> ContentVersion | None:
    queryset = ContentVersion.objects.filter(
        item__task_type=task_type, status=PublicationStatus.PUBLISHED
    )
    if difficulty is not None:
        match = queryset.filter(item__difficulty=difficulty).order_by("item__slug").first()
        if match is not None:
            return match
    return queryset.order_by("item__difficulty", "item__slug").first()


def recommendation_payload(user) -> dict:
    """Pick the next activity: weakest skill, target difficulty, task family.

    A task family is preferred by open-mistake count, then by being unpractised,
    then by lowest accuracy; all ties resolve to the official part order. When no
    published prompt exists the response returns ``recommendation: null`` with a
    human-readable reason instead of guessing.
    """
    progress = progress_payload(user)
    priorities = _skill_priority(progress)
    basis: dict = {
        "weakest_skill": None,
        "skill_priorities": priorities,
        "selected_task_type": None,
        "target_difficulty": None,
        "reasoning": "No skill data yet.",
    }
    if not priorities:
        return {
            "recommendation": None,
            "basis": basis,
            "disclaimer": RECOMMENDATION_DISCLAIMER,
        }

    weakest = max(priorities, key=lambda skill: priorities[skill])
    summaries = {summary["skill"]: summary for summary in progress["skills"]}
    task_stats = {stat["task_type"]: stat for stat in progress["task_types"]}
    difficulty = _recommended_difficulty(summaries[weakest])
    basis["weakest_skill"] = weakest
    basis["target_difficulty"] = difficulty

    mistake_counts = {
        row["task_type_id"]: row["count"]
        for row in MistakeRecord.objects.filter(
            user=user, skill=weakest, state=MistakeState.OPEN
        )
        .values("task_type_id")
        .annotate(count=Count("id"))
    }
    task_types = list(
        TaskType.objects.filter(skill=weakest, is_active=True).order_by("part_number")
    )
    if not task_types:
        basis["reasoning"] = f"No active task families exist for {SKILL_LABELS[weakest]}."
        return {
            "recommendation": None,
            "basis": basis,
            "disclaimer": RECOMMENDATION_DISCLAIMER,
        }

    selected = None
    with_mistakes = [
        task for task in task_types if mistake_counts.get(task.code, 0) > 0
    ]
    if with_mistakes:
        selected = max(with_mistakes, key=lambda task: mistake_counts[task.code])
        reason_tail = (
            f"You have {mistake_counts[selected.code]} open mistake pattern(s) in "
            f"{selected.title}."
        )
    else:
        unpractised = [task for task in task_types if task_stats.get(task.code) is None]
        if unpractised:
            selected = unpractised[0]
            reason_tail = f"You have not practised {selected.title} yet."
        else:
            def _accuracy(task: TaskType) -> int:
                accuracy = task_stats[task.code]["accuracy_percent"]
                return accuracy if accuracy is not None else 100

            selected = min(
                task_types,
                key=lambda task: (_accuracy(task), task.part_number),
            )
            reason_tail = (
                f"{selected.title} is your weakest practised task family "
                f"({task_stats[selected.code]['accuracy_percent']}% accuracy)."
            )
    basis["selected_task_type"] = selected.code

    version = _published_for(selected, difficulty)
    if version is None:
        version = (
            ContentVersion.objects.filter(
                item__task_type__skill=weakest, status=PublicationStatus.PUBLISHED
            )
            .order_by("item__difficulty", "item__slug")
            .first()
        )
    if version is None:
        basis["reasoning"] = (
            f"No published practice prompt is available for {SKILL_LABELS[weakest]} yet."
        )
        return {
            "recommendation": None,
            "basis": basis,
            "disclaimer": RECOMMENDATION_DISCLAIMER,
        }

    reason = (
        f"{SKILL_LABELS[weakest]} is your weakest skill "
        f"(priority {priorities[weakest]:g}). {reason_tail} This prompt is difficulty "
        f"{version.item.difficulty}, estimated level {version.item.estimated_level}."
    )
    basis["reasoning"] = reason
    return {
        "recommendation": {
            "content_slug": version.item.slug,
            "title": version.item.title,
            "skill": weakest,
            "task_type": selected.code,
            "difficulty": version.item.difficulty,
            "estimated_level": version.item.estimated_level,
            "reason": reason,
            "launch_url": DESTINATIONS[weakest],
        },
        "basis": basis,
        "disclaimer": RECOMMENDATION_DISCLAIMER,
    }
