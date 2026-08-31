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
from apps.assessments.models import (
    AssessmentSession,
    ObjectiveResult,
    SessionMode,
    SessionState,
    SpeakingSubmission,
    WritingSubmission,
)
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

# Number of most-recent results shown on the dashboard. Small and privacy-safe:
# only the learner's own submitted/estimated outcomes, with no prompt text.
RECENT_RESULTS_LIMIT = 5

STREAK_RULE = (
    "Unique submitted/completed activity dates in the learner's profile timezone. "
    "The streak is anchored on today when today has activity, otherwise on yesterday. "
    "Future dates are ignored."
)

SIGNALS_NOTE = (
    "Cross-skill comparison uses an unofficial practice planning indicator: objective "
    "accuracy is 0-100 for Listening/Reading, and the AI-assisted midpoint is divided by "
    "12 and multiplied by 100 for Writing/Speaking. Unpractised skills are shown as "
    "needs-attention rather than silently scored zero."
)

DESTINATIONS = {
    Skill.READING: "/practice",
    Skill.LISTENING: "/practice/listening",
    Skill.WRITING: "/practice/writing",
    Skill.SPEAKING: "/practice/speaking",
}

# Deterministic, documented weights for the overall readiness planning indicator.
# They always sum to 1.0 and are shown to the learner alongside each component.
READINESS_WEIGHTS = {
    "coverage": 0.30,
    "recency": 0.25,
    "volume": 0.25,
    "performance": 0.20,
}
READINESS_FORMULA = "0.30 × coverage + 0.25 × recency + 0.25 × volume + 0.20 × performance"
READINESS_DISCLAIMER = (
    "This is an unofficial practice planning indicator, not a CELPIP score and not a "
    "score prediction. It weighs skill coverage, recency, practice volume, and available "
    "practice signals to help you decide what to do next. Listening/Reading use objective "
    "accuracy; Writing/Speaking use the AI-assisted midpoint divided by 12 and multiplied "
    "by 100. These measures are not directly comparable to each other or to an official "
    "CELPIP level."
)


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
    # Manual completions must survive auto-regeneration (which runs after every
    # practice submission and feedback completion). Key by (date, skill) because
    # the rotation schedules at most one task per skill per day, so the same
    # evidence maps cleanly onto the regenerated schedule. Skipped tasks are
    # carried too: a learner who skipped once shouldn't be silently re-asked.
    carry = {}
    if previous:
        carry = {
            (task.scheduled_date, task.skill): (task.state, task.completed_at)
            for task in previous.tasks.exclude(state=StudyTaskState.PENDING)
        }
    if previous:
        previous.is_active = False
        previous.save(update_fields=["is_active"])
    plan = StudyPlan.objects.create(
        user=user,
        version=version,
        name=(previous.name if previous else ""),
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
    # With an exam date, keep generating the schedule all the way to the
    # learner's exam. Without one, retain the short rolling planning window.
    # The previous 14-day cap applied even when an exam was configured, which
    # made an October exam appear to end in September.
    end = (
        profile.exam_date
        if profile.exam_date and profile.exam_date >= local_today
        else local_today + timedelta(days=13)
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
            carried = carry.get((scheduled_date, skill))
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
                state=(carried[0] if carried else StudyTaskState.PENDING),
                completed_at=(carried[1] if carried else None),
            )
    return plan


def _task_payload(task: StudyTask) -> dict:
    return {
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


def plan_payload(plan: StudyPlan) -> dict:
    return {
        "id": plan.pk,
        "version": plan.version,
        "generated_at": plan.generated_at,
        "name": plan.name,
        "reason_summary": plan.reason_summary,
        "tasks": [_task_payload(task) for task in plan.tasks.select_related("task_type")],
    }


def study_plan_consistency(user, days: int = 14) -> dict:
    """Per-day completion evidence for the Study Plan page's streak bar.

    Buckets completed Study tasks by calendar date in the learner's timezone and
    records which skills were completed that day. The streak is computed purely
    from study-task completions (not general activity, unlike the dashboard's
    streak) so the bar answers "have I kept up with my plan".
    """
    profile = _profile_for(user)
    try:
        zone = ZoneInfo(profile.timezone)
    except Exception:
        zone = ZoneInfo("UTC")
    today = timezone.now().astimezone(zone).date()
    completed = StudyTask.objects.filter(
        plan__user=user, state=StudyTaskState.COMPLETED, completed_at__isnull=False
    )
    completions: dict = {}
    for task in completed:
        day = task.completed_at.astimezone(zone).date()
        completions.setdefault(day, set()).add(task.skill)

    streak = study_streak({day for day, _ in completions.items()}, today)

    start = today - timedelta(days=days - 1)
    days_payload = []
    for offset in range(days):
        day = start + timedelta(days=offset)
        day_skills = completions.get(day, set())
        days_payload.append(
            {
                "date": day.isoformat(),
                "skills": {skill: skill in day_skills for skill in SKILLS},
                "completed": bool(day_skills),
            }
        )
    return {
        "streak": streak,
        "days": days_payload,
        "window_days": days,
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


# ── Dashboard selector ───────────────────────────────────────────────────────
# A cohesive read model for the authenticated dashboard. It reuses the progress
# selector for per-skill measures, then layers on totals, streak, recent results,
# practice signals, and a transparent readiness planning indicator. No schema
# changes are required: every value is derived from already-stored evidence.


def _activity_dates(user, zone: ZoneInfo) -> set:
    """Unique calendar dates (in ``zone``) with submitted/completed activity.

    Sources: objective submissions, writing submissions, speaking submissions,
    and completed study tasks. Future dates are ignored by the streak logic.
    """
    dates = set()
    scored_dates = ObjectiveResult.objects.filter(session__user=user).values_list(
        "scored_at", flat=True
    )
    dates.update(value.astimezone(zone).date() for value in scored_dates)

    writing_dates = WritingSubmission.objects.filter(
        session_item__session__user=user, submitted_at__isnull=False
    ).values_list("submitted_at", flat=True)
    dates.update(value.astimezone(zone).date() for value in writing_dates)

    speaking_dates = SpeakingSubmission.objects.filter(
        session_item__session__user=user, submitted_at__isnull=False
    ).values_list("submitted_at", flat=True)
    dates.update(value.astimezone(zone).date() for value in speaking_dates)

    task_dates = StudyTask.objects.filter(
        plan__user=user, state=StudyTaskState.COMPLETED, completed_at__isnull=False
    ).values_list("completed_at", flat=True)
    dates.update(value.astimezone(zone).date() for value in task_dates)
    return dates


def study_streak(activity_dates: set, today) -> dict:
    """Count consecutive activity days ending today or yesterday.

    The anchor is today when today has activity, otherwise yesterday. Future
    dates are ignored. A learner with no recent activity has a zero-day streak.
    """
    active = {day for day in activity_dates if day <= today}
    if today in active:
        anchor = today
        anchor_label = "today"
    elif today - timedelta(days=1) in active:
        anchor = today - timedelta(days=1)
        anchor_label = "yesterday"
    else:
        return {"days": 0, "active_today": False, "anchor": None}

    days = 0
    cursor = anchor
    while cursor in active:
        days += 1
        cursor -= timedelta(days=1)
    return {"days": days, "active_today": anchor == today, "anchor": anchor_label}


def _recent_results(user) -> list[dict]:
    """Merge objective accuracy and AI-assisted estimates, newest first."""
    entries = []
    objective = list(
        ObjectiveResult.objects.filter(session__user=user)
        .select_related("session")
        .prefetch_related("session__items")
    )
    for result in objective:
        item = result.session.items.first()
        snapshot = item.snapshot if item else {}
        value = (
            round(100 * result.raw_correct / result.raw_possible)
            if result.raw_possible
            else None
        )
        entries.append(
            {
                "date": result.scored_at,
                "skill": snapshot.get("skill"),
                "task_type": snapshot.get("task_type"),
                "title": snapshot.get("title", snapshot.get("task_type", "")),
                "measure": "accuracy_percent",
                "value": value,
                "label": "Practice accuracy",
                "destination": DESTINATIONS.get(snapshot.get("skill"), "/practice"),
            }
        )

    feedback = AIFeedback.objects.filter(session_item__session__user=user).select_related(
        "session_item"
    )
    for artifact in feedback:
        snapshot = artifact.session_item.snapshot
        low = artifact.assessment["estimated_level_low"]
        high = artifact.assessment["estimated_level_high"]
        entries.append(
            {
                "date": artifact.created_at,
                "skill": snapshot.get("skill"),
                "task_type": snapshot.get("task_type"),
                "title": snapshot.get("title", snapshot.get("task_type", "")),
                "measure": "estimated_midpoint",
                "value": round((low + high) / 2, 1),
                "label": "AI-assisted practice estimate",
                "destination": DESTINATIONS.get(snapshot.get("skill"), "/practice"),
            }
        )

    entries.sort(key=lambda entry: entry["date"], reverse=True)
    return [
        {**entry, "date": entry["date"].isoformat()}
        for entry in entries[:RECENT_RESULTS_LIMIT]
    ]


def _practice_signal(summary: dict) -> dict | None:
    """Normalise one skill summary to a 0-100 planning signal, or None.

    Objective accuracy stays 0-100. An AI-assisted Writing/Speaking estimate is
    normalised as midpoint ÷ 12 × 100. Unpractised skills return None.
    """
    if summary["accuracy_percent"] is not None:
        value = summary["accuracy_percent"]
        return {
            "measure": "accuracy_percent",
            "value": value,
            "planning_signal": value,
            "basis": f"{value}% practice accuracy",
        }
    if summary["estimate_low"] is not None:
        midpoint = round((summary["estimate_low"] + summary["estimate_high"]) / 2, 1)
        normalised = round(midpoint / 12 * 100)
        return {
            "measure": "estimated_midpoint",
            "value": midpoint,
            "planning_signal": normalised,
            "basis": f"AI-assisted midpoint {midpoint}/12 (≈{normalised}% planning signal)",
        }
    return None


def _practice_signals(skills: list[dict]) -> tuple[dict | None, dict | None]:
    """Return the strongest and needs-attention practice signals.

    Unpractised skills rank first for needs-attention (no evidence), then the
    lowest planning signal among practised skills.
    """
    practised = []
    unpractised = []
    for summary in skills:
        signal = _practice_signal(summary)
        entry = {"skill": summary["skill"], "attempts": summary["attempts"]}
        if signal:
            practised.append({**entry, **signal})
        else:
            unpractised.append(summary["skill"])

    strongest = max(practised, key=lambda item: item["planning_signal"]) if practised else None

    if unpractised:
        needs_attention = {
            "skill": unpractised[0],
            "measure": None,
            "value": None,
            "planning_signal": None,
            "attempts": 0,
            "basis": "No practice recorded yet",
        }
    else:
        needs_attention = min(practised, key=lambda item: item["planning_signal"])

    return strongest, needs_attention


def _completed_attempts(user) -> int:
    """Count the learner's completed attempts from submitted sessions.

    A learner completes an attempt when their owned session is submitted, even
    if AI feedback is still queued, has failed, or is unavailable. Each
    submitted session is one attempt. Mock sessions are excluded because a
    single mock attempt fans out into many per-task sessions and is reported
    separately on the mock results page.
    """
    return (
        AssessmentSession.objects.filter(user=user, state=SessionState.SUBMITTED)
        .exclude(mode=SessionMode.MOCK)
        .count()
    )


def _readiness_indicator(
    skills: list[dict], activity_dates: set, today, completed_attempts: int
) -> dict:
    """Transparent planning indicator from coverage, recency, volume, performance.

    Coverage and performance stay evidence-based (objective results or succeeded
    AI feedback); volume counts every completed attempt (submitted session),
    whether or not feedback has been produced yet.
    """
    practised = sum(1 for summary in skills if summary["attempts"] > 0)

    coverage_value = round(100 * practised / len(SKILLS))
    volume_value = min(100, completed_attempts * 10)

    past_dates = [day for day in activity_dates if day <= today]
    if past_dates:
        days_since = (today - max(past_dates)).days
        recency_value = max(0, 100 - 10 * days_since)
        recency_raw = f"Most recent activity {days_since} day(s) ago"
    else:
        recency_value = 0
        recency_raw = "No activity yet"

    signals = [signal for summary in skills if (signal := _practice_signal(summary))]
    performance_value = (
        round(sum(signal["planning_signal"] for signal in signals) / len(signals))
        if signals
        else 0
    )

    components = [
        {
            "key": "coverage",
            "label": "Skill coverage",
            "weight": READINESS_WEIGHTS["coverage"],
            "value": coverage_value,
            "raw": f"{practised} of {len(SKILLS)} skills practised",
            "explanation": (
                "The share of the four CELPIP skills with at least one objective result "
                "or AI-assisted estimate."
            ),
        },
        {
            "key": "recency",
            "label": "Recency",
            "weight": READINESS_WEIGHTS["recency"],
            "value": recency_value,
            "raw": recency_raw,
            "explanation": (
                "100 for activity today, minus 10 per full day since your most recent "
                "activity (never below 0)."
            ),
        },
        {
            "key": "volume",
            "label": "Practice volume",
            "weight": READINESS_WEIGHTS["volume"],
            "value": volume_value,
            "raw": f"{completed_attempts} completed attempt(s)",
            "explanation": "10 points per completed attempt, capped at 100.",
        },
        {
            "key": "performance",
            "label": "Performance signal",
            "weight": READINESS_WEIGHTS["performance"],
            "value": performance_value,
            "raw": f"{len(signals)} skill(s) with evidence",
            "explanation": (
                "Average of per-skill practice planning signals (objective accuracy for "
                "Listening/Reading; AI-assisted midpoint ÷ 12 × 100 for Writing/Speaking)."
            ),
        },
    ]

    if completed_attempts == 0:
        state = "insufficient_evidence"
        indicator = None
        explanation = (
            "There is not enough practice evidence yet. Complete an attempt in any skill "
            "to see a planning indicator."
        )
    else:
        state = "estimated"
        indicator = round(sum(component["weight"] * component["value"] for component in components))
        explanation = (
            "A weighted planning aid, not a score. The components below show exactly what "
            "drives it and what each measure means."
        )

    return {
        "label": "Practice planning indicator",
        "indicator": indicator,
        "state": state,
        "is_official": False,
        "formula": READINESS_FORMULA,
        "components": components,
        "explanation": explanation,
        "disclaimer": READINESS_DISCLAIMER,
    }


def _today_and_next(plan: StudyPlan | None, today) -> tuple[list[dict], dict | None]:
    if plan is None:
        return [], None
    tasks = list(plan.tasks.all())
    today_tasks = [_task_payload(task) for task in tasks if task.scheduled_date == today]
    upcoming = [
        task
        for task in tasks
        if task.scheduled_date > today and task.state == StudyTaskState.PENDING
    ]
    upcoming.sort(key=lambda task: (task.scheduled_date, task.order))
    next_upcoming = _task_payload(upcoming[0]) if upcoming else None
    return today_tasks, next_upcoming


def dashboard_payload(user) -> dict:
    """Authenticated dashboard read model (see module docstring above)."""
    profile = _profile_for(user)
    progress = progress_payload(user)
    try:
        zone = ZoneInfo(profile.timezone)
    except Exception:
        zone = ZoneInfo("UTC")
    today = timezone.now().astimezone(zone).date()

    activity_dates = _activity_dates(user, zone)
    streak = study_streak(activity_dates, today)

    skills = progress["skills"]
    strongest, needs_attention = _practice_signals(skills)
    completed_attempts = _completed_attempts(user)

    plan = (
        StudyPlan.objects.filter(user=user, is_active=True)
        .prefetch_related("tasks__task_type")
        .first()
    )
    today_tasks, next_upcoming = _today_and_next(plan, today)

    return {
        "skills": skills,
        "task_types": progress["task_types"],
        "trends": progress["trends"],
        "coverage": progress["coverage"],
        "totals": {
            "objective_questions_completed": sum(
                summary["questions_total"] for summary in skills
            ),
            "completed_attempts": completed_attempts,
        },
        "streak": {
            **streak,
            "timezone": profile.timezone,
            "rule": STREAK_RULE,
        },
        "recent_results": _recent_results(user),
        "signals": {
            "strongest": strongest,
            "needs_attention": needs_attention,
            "note": SIGNALS_NOTE,
        },
        "readiness": _readiness_indicator(skills, activity_dates, today, completed_attempts),
        "today": {
            "date": today.isoformat(),
            "timezone": profile.timezone,
            "tasks": today_tasks,
        },
        "next_upcoming_task": next_upcoming,
        "disclaimer": "Practice analytics are not official CELPIP results.",
    }
