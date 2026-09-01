"""Transactional assembly, timing, progression, and results for mock attempts."""

from __future__ import annotations

import random
from datetime import date, timedelta

from django.db import transaction
from django.db.models import Count
from django.utils import timezone

from apps.ai_services.models import AIFeedback
from apps.assessments.models import (
    AssessmentSession,
    ObjectiveResult,
    SessionItem,
    SessionMode,
    SessionState,
)
from apps.assessments.services import _snapshot
from apps.content.models import (
    ContentVersion,
    PublicationStatus,
    Skill,
    TaskType,
    TestFormatVersion,
)

from .models import MockAttempt, MockState, MockTask, MockTaskState

FORMAT_CODE = "celpip-general-2026-08"
SOURCE_URL = "https://www.celpip.ca/take-celpip/test-format/"
COMPONENT_ORDER = [Skill.LISTENING, Skill.READING, Skill.WRITING, Skill.SPEAKING]
COMPONENT_TIMINGS = {
    Skill.LISTENING: {"public_range_minutes": [46, 55], "mock_seconds": 3300},
    Skill.READING: {"public_range_minutes": [43, 56], "mock_seconds": 3360},
    Skill.WRITING: {"public_range_minutes": [53, 53], "mock_seconds": 3180},
    Skill.SPEAKING: {"public_range_minutes": [15, 15], "mock_seconds": 900},
}
OFFICIAL_COUNTS = {
    "listening_problem_solving": 8,
    "listening_daily_conversation": 5,
    "listening_information": 6,
    "listening_news": 5,
    "listening_discussion": 8,
    "listening_viewpoints": 6,
    "reading_correspondence": 11,
    "reading_apply_diagram": 8,
    "reading_information": 9,
    "reading_viewpoints": 10,
    "writing_email": 1,
    "writing_survey": 1,
    "speaking_advice": 1,
    "speaking_experience": 1,
    "speaking_scene": 1,
    "speaking_predictions": 1,
    "speaking_compare_persuade": 1,
    "speaking_difficult_situation": 1,
    "speaking_opinions": 1,
    "speaking_unusual": 1,
}
COMPACT_SCOPE = "compact_task_family_mock"
FULL_LENGTH_SCOPE = "full_length_simulation"

LIMITATION = (
    "This compact task-family mock covers every current CELPIP-General task family and "
    "uses official component time boxes. Its original starter bank has fewer objective "
    "questions than the live test, so question volume and practice accuracy are not an "
    "official test simulation or score conversion."
)

FULL_LENGTH_LIMITATION = (
    "Full simulation — unofficial. This mock uses the current official Listening and "
    "Reading question counts and all eight Speaking tasks, assembled from original, "
    "human-reviewed content in the official section order and official time boxes. It "
    "reproduces official test STRUCTURE only: content, audio, and scoring are original "
    "to this project, not an official CELPIP test, and raw practice accuracy is never "
    "converted to an official CELPIP score or level. Some Listening/Reading items may be "
    "simulated unscored development content, indistinguishable during the attempt, "
    "exactly as CELPIP describes for its own live test."
)

# Content authored for progressive Guided/Independent/Challenge practice stages
# (see content.practice_bank_expansion) reuses the same reviewed scenario with
# only difficulty relabelling, so combining several stages of one scenario
# inside a single mock attempt would feel repetitive rather than varied. Full
# mock assembly draws only from the original, non-stage-expanded tier.
_STAGE_SLUG_SUFFIXES = ("-guided-stage", "-independent-stage", "-challenge-stage")


def _is_full_length_eligible(item_slug: str) -> bool:
    return not item_slug.endswith(_STAGE_SLUG_SUFFIXES)


class MockError(Exception):
    code = "mock_error"


class MockUnavailable(MockError):
    code = "mock_unavailable"


class InvalidTransition(MockError):
    code = "invalid_mock_transition"


class ResultsEmbargoed(MockError):
    code = "mock_results_embargoed"


def ensure_format() -> TestFormatVersion:
    structure = [
        {
            "skill": task.skill,
            "task_type": task.code,
            "part_number": task.part_number,
            "official_question_or_component_count": OFFICIAL_COUNTS.get(task.code, 1),
        }
        for task in TaskType.objects.filter(code__in=OFFICIAL_COUNTS).order_by(
            "skill", "part_number"
        )
    ]
    # Order by the actual four-component sequence, not alphabetically.
    structure.sort(key=lambda row: (COMPONENT_ORDER.index(row["skill"]), row["part_number"]))
    format_version, _ = TestFormatVersion.objects.update_or_create(
        code=FORMAT_CODE,
        defaults={
            "name": "CELPIP-General format verified August 2026",
            "is_active": True,
            "verified_on": date(2026, 8, 29),
            "official_source_urls": [SOURCE_URL],
            "notes": "Public structural facts only; all practice content is original.",
            "component_order": COMPONENT_ORDER,
            "component_timings": COMPONENT_TIMINGS,
            "task_structure": structure,
        },
    )
    return format_version


@transaction.atomic
def create_attempt(user, *, scope: str = COMPACT_SCOPE) -> MockAttempt:
    """Assemble a frozen mock attempt.

    ``scope=COMPACT_SCOPE`` (default) keeps the original one-item-per-task-type
    simulation. ``scope=FULL_LENGTH_SCOPE`` assembles each Listening/Reading
    section to the current official question count from several distinct
    content versions; see ``_create_full_length_attempt``.
    """
    if scope == FULL_LENGTH_SCOPE:
        return _create_full_length_attempt(user)
    return _create_compact_attempt(user)


def _create_compact_attempt(user) -> MockAttempt:
    format_version = ensure_format()
    expected = list(
        TaskType.objects.filter(code__in=OFFICIAL_COUNTS, is_active=True).prefetch_related(
            "content_items__versions"
        )
    )
    expected.sort(key=lambda task: (COMPONENT_ORDER.index(task.skill), task.part_number))
    if len(expected) != 20:
        raise MockUnavailable("All 20 CELPIP-General task families must be available.")
    selected: list[tuple[TaskType, ContentVersion]] = []
    for task_type in expected:
        version = (
            ContentVersion.objects.filter(
                item__task_type=task_type, status=PublicationStatus.PUBLISHED
            )
            .select_related("item__task_type")
            .prefetch_related("questions__choices")
            .order_by("item__slug", "-version")
            .first()
        )
        if version is None:
            raise MockUnavailable(f"No reviewed prompt is available for {task_type.title}.")
        selected.append((task_type, version))
    format_snapshot = {
        "code": format_version.code,
        "verified_on": format_version.verified_on.isoformat(),
        "official_source_urls": format_version.official_source_urls,
        "component_order": COMPONENT_ORDER,
        "component_timings": COMPONENT_TIMINGS,
        "task_structure": format_version.task_structure,
        "scope": "compact_task_family_mock",
        "limitation": LIMITATION,
    }
    attempt = MockAttempt.objects.create(
        user=user, format_version=format_version, format_snapshot=format_snapshot
    )
    for order, (task_type, version) in enumerate(selected, start=1):
        frozen = _snapshot(version)
        session = AssessmentSession.objects.create(user=user, mode=SessionMode.MOCK)
        SessionItem.objects.create(
            session=session, content_version=version, order=1, snapshot=frozen
        )
        MockTask.objects.create(
            attempt=attempt,
            order=order,
            section=task_type.skill,
            task_type=task_type.code,
            content_version=version,
            session=session,
            snapshot=frozen,
        )
    return attempt


def _exact_sum_combo(
    sized_versions: list[tuple[ContentVersion, int]], target: int
) -> list[tuple[ContentVersion, int]] | None:
    """Backtrack to a distinct subset whose question counts sum exactly to ``target``.

    ``sized_versions`` should already be shuffled by the caller: backtracking
    returns the first exact match it finds, so shuffle order is what makes
    repeated calls prefer different combinations. The pool per task type is
    small (roughly 5-9 versions), so this is fast despite being exponential
    in the worst case.
    """

    def backtrack(index: int, remaining: int) -> list[tuple[ContentVersion, int]] | None:
        if remaining == 0:
            return []
        if remaining < 0 or index >= len(sized_versions):
            return None
        version, qcount = sized_versions[index]
        if qcount <= remaining:
            rest = backtrack(index + 1, remaining - qcount)
            if rest is not None:
                return [(version, qcount)] + rest
        return backtrack(index + 1, remaining)

    return backtrack(0, target)


def _eligible_versions(task_type: TaskType) -> list[ContentVersion]:
    versions = list(
        ContentVersion.objects.filter(
            item__task_type=task_type, status=PublicationStatus.PUBLISHED
        )
        .select_related("item__task_type")
        .prefetch_related("questions__choices")
        .annotate(qcount=Count("questions"))
    )
    return [version for version in versions if _is_full_length_eligible(version.item.slug)]


def _select_objective_combo(
    task_type: TaskType, target: int, recent_ids: set[int]
) -> list[tuple[ContentVersion, int]]:
    """Pick distinct, published, non-stage content versions summing to ``target``.

    Versions used by this user's recent full-length attempts for this task
    type are tried first as an excluded pool, so a repeated mock tends toward
    a different combination; if no exact combination avoids them, reuse is
    allowed rather than failing the whole attempt.
    """
    versions = _eligible_versions(task_type)
    sized = [(version, version.qcount) for version in versions if version.qcount]
    random.shuffle(sized)
    fresh = [pair for pair in sized if pair[0].id not in recent_ids]
    combo = _exact_sum_combo(fresh, target) or _exact_sum_combo(sized, target)
    if combo is None:
        raise MockUnavailable(
            f"No combination of reviewed {task_type.title} content reaches the official "
            f"{target}-question count."
        )
    return combo


def _pick_single_version(task_type: TaskType, recent_ids: set[int]) -> ContentVersion:
    versions = _eligible_versions(task_type)
    if not versions:
        raise MockUnavailable(f"No reviewed prompt is available for {task_type.title}.")
    random.shuffle(versions)
    fresh = [version for version in versions if version.id not in recent_ids]
    return fresh[0] if fresh else versions[0]


def _create_full_length_attempt(user) -> MockAttempt:
    format_version = ensure_format()
    expected = list(TaskType.objects.filter(code__in=OFFICIAL_COUNTS, is_active=True))
    expected.sort(key=lambda task: (COMPONENT_ORDER.index(task.skill), task.part_number))
    if len(expected) != 20:
        raise MockUnavailable("All 20 CELPIP-General task families must be available.")

    recent_ids = set(
        MockTask.objects.filter(
            attempt__user=user, attempt__scope=FULL_LENGTH_SCOPE
        ).values_list("content_version_id", flat=True)
    )

    # (task_type, [(version, qcount), ...], unscored_version_ids)
    selections: list[tuple[TaskType, list[tuple[ContentVersion, int]], set[int]]] = []
    for task_type in expected:
        target = OFFICIAL_COUNTS[task_type.code]
        if task_type.skill in (Skill.WRITING, Skill.SPEAKING):
            version = _pick_single_version(task_type, recent_ids)
            selections.append((task_type, [(version, 0)], set()))
            continue
        combo = _select_objective_combo(task_type, target, recent_ids)
        unscored_ids: set[int] = set()
        # A section assembled from more than two distinct sets needed extra
        # content beyond a natural pairing to reach the exact official count.
        # That extra, smallest set becomes the simulated-unscored item —
        # indistinguishable during the attempt, excluded from raw scoring.
        if len(combo) > 2:
            smallest = min(combo, key=lambda pair: pair[1])
            unscored_ids = {smallest[0].id}
        selections.append((task_type, combo, unscored_ids))

    format_snapshot = {
        "code": format_version.code,
        "verified_on": format_version.verified_on.isoformat(),
        "official_source_urls": format_version.official_source_urls,
        "component_order": COMPONENT_ORDER,
        "component_timings": COMPONENT_TIMINGS,
        "task_structure": format_version.task_structure,
        "scope": FULL_LENGTH_SCOPE,
        "limitation": FULL_LENGTH_LIMITATION,
    }
    attempt = MockAttempt.objects.create(
        user=user, scope=FULL_LENGTH_SCOPE, format_version=format_version,
        format_snapshot=format_snapshot,
    )
    order = 0
    for task_type, combo, unscored_ids in selections:
        for version, _qcount in sorted(combo, key=lambda pair: pair[0].id):
            order += 1
            frozen = _snapshot(version)
            session = AssessmentSession.objects.create(user=user, mode=SessionMode.MOCK)
            SessionItem.objects.create(
                session=session, content_version=version, order=1, snapshot=frozen
            )
            MockTask.objects.create(
                attempt=attempt,
                order=order,
                section=task_type.skill,
                task_type=task_type.code,
                content_version=version,
                session=session,
                snapshot=frozen,
                is_simulated_unscored=version.id in unscored_ids,
            )
    return attempt


def _start_section(attempt: MockAttempt, task: MockTask, now) -> None:
    seconds = attempt.format_snapshot["component_timings"][task.section]["mock_seconds"]
    deadline = now + timedelta(seconds=seconds)
    attempt.current_section = task.section
    attempt.current_order = task.order
    attempt.section_started_at = now
    attempt.section_deadline_at = deadline
    attempt.state = MockState.ACTIVE
    task.state = MockTaskState.CURRENT
    task.save(update_fields=["state"])
    AssessmentSession.objects.filter(
        mock_task__attempt=attempt,
        mock_task__section=task.section,
        state=SessionState.ACTIVE,
    ).update(deadline_at=deadline)


def _complete(attempt: MockAttempt, now) -> None:
    attempt.state = MockState.COMPLETED
    attempt.completed_at = now
    attempt.section_deadline_at = None
    attempt.section_started_at = None


def _expire_locked(attempt: MockAttempt, now) -> bool:
    if (
        attempt.state != MockState.ACTIVE
        or attempt.section_deadline_at is None
        or attempt.section_deadline_at > now
    ):
        return False
    remaining = attempt.tasks.filter(
        section=attempt.current_section,
        order__gte=attempt.current_order,
        state__in=[MockTaskState.PENDING, MockTaskState.CURRENT],
    )
    # A current child whose session was already submitted is recorded as
    # submitted, not skipped; only the unfinished remainder is skipped.
    submitted = remaining.filter(session__state=SessionState.SUBMITTED)
    unfinished = remaining.filter(session__state=SessionState.ACTIVE)
    submitted.update(state=MockTaskState.SUBMITTED)
    session_ids = list(unfinished.values_list("session_id", flat=True))
    unfinished.update(state=MockTaskState.SKIPPED)
    AssessmentSession.objects.filter(id__in=session_ids, state=SessionState.ACTIVE).update(
        state=SessionState.SUBMITTED, submitted_at=now
    )
    next_task = (
        attempt.tasks.filter(order__gt=attempt.current_order)
        .exclude(section=attempt.current_section)
        .first()
    )
    if next_task is None:
        _complete(attempt, now)
    else:
        _start_section(attempt, next_task, now)
    attempt.save()
    return True


@transaction.atomic
def start_attempt(attempt_id, user) -> tuple[MockAttempt, bool]:
    attempt = MockAttempt.objects.select_for_update().get(pk=attempt_id, user=user)
    if attempt.state != MockState.READY:
        _expire_locked(attempt, timezone.now())
        return attempt, True
    now = timezone.now()
    first = attempt.tasks.first()
    if first is None:
        raise MockUnavailable("This mock contains no tasks.")
    attempt.started_at = now
    _start_section(attempt, first, now)
    attempt.save()
    return attempt, False


@transaction.atomic
def refresh_attempt(attempt_id, user) -> MockAttempt:
    attempt = MockAttempt.objects.select_for_update().get(pk=attempt_id, user=user)
    _expire_locked(attempt, timezone.now())
    return attempt


@transaction.atomic
def advance_attempt(attempt_id, user, *, expected_order: int) -> tuple[MockAttempt, bool]:
    attempt = MockAttempt.objects.select_for_update().get(pk=attempt_id, user=user)
    now = timezone.now()
    if _expire_locked(attempt, now):
        return attempt, False
    if attempt.state == MockState.COMPLETED:
        return attempt, True
    if attempt.state != MockState.ACTIVE:
        raise InvalidTransition("Start this mock before advancing.")
    if expected_order < attempt.current_order:
        return attempt, True
    if expected_order != attempt.current_order:
        raise InvalidTransition("The requested task is not current.")
    task = attempt.tasks.select_related("session").get(order=attempt.current_order)
    if task.session.state != SessionState.SUBMITTED:
        raise InvalidTransition("Submit the current task before continuing.")
    task.state = MockTaskState.SUBMITTED
    task.save(update_fields=["state"])
    next_task = attempt.tasks.filter(order=task.order + 1).first()
    if next_task is None:
        _complete(attempt, now)
    elif next_task.section == task.section:
        next_task.state = MockTaskState.CURRENT
        next_task.save(update_fields=["state"])
        attempt.current_order = next_task.order
    else:
        _start_section(attempt, next_task, now)
    attempt.save()
    return attempt, False


def task_kind(task: MockTask) -> str:
    if task.section in (Skill.LISTENING, Skill.READING):
        return "objective"
    return task.section


def exam_rules(attempt: MockAttempt) -> dict:
    """Explicit mock exam-mode contract for a client timer and submit flow.

    Timing reflects the live section only while the attempt is active; before
    start and after completion there is no running clock. Everything is derived
    from stored state, never guessed client-side, so a resume mid-section shows
    the authoritative remaining time.
    """
    now = timezone.now()
    timing: dict = {
        "running": attempt.state == MockState.ACTIVE,
        "auto_submits_on_expiry": True,
    }
    if attempt.state == MockState.ACTIVE:
        seconds = attempt.format_snapshot["component_timings"][attempt.current_section][
            "mock_seconds"
        ]
        remaining_seconds = None
        if attempt.section_deadline_at:
            remaining_seconds = max(0, int((attempt.section_deadline_at - now).total_seconds()))
        timing |= {
            "per_section_seconds": seconds,
            "section": attempt.current_section,
            "section_started_at": attempt.section_started_at,
            "section_deadline_at": attempt.section_deadline_at,
            "remaining_seconds": remaining_seconds,
            "expired": remaining_seconds == 0 if remaining_seconds is not None else None,
        }
    return {
        "timing": timing,
        "submission": {
            "editable_after_submit": False,
            "results_embargoed_until_complete": True,
        },
        "replay": {
            "objective_answers_replayable": False,
            "speaking_retry_allowed": False,
            "audio_playback": "one_play",
        },
    }


def attempt_payload(attempt: MockAttempt, *, include_tasks: bool = True) -> dict:
    current = None
    if attempt.state == MockState.ACTIVE:
        task = attempt.tasks.select_related("session").get(order=attempt.current_order)
        current = {
            "order": task.order,
            "section": task.section,
            "task_type": task.task_type,
            "title": task.snapshot["title"],
            "session_id": str(task.session_id),
            "kind": task_kind(task),
            "launch_url": f"/mock/{attempt.id}/task/{task.order}",
        }
    payload = {
        "id": str(attempt.id),
        "state": attempt.state,
        "scope": attempt.scope,
        "created_at": attempt.created_at,
        "started_at": attempt.started_at,
        "completed_at": attempt.completed_at,
        "server_now": timezone.now(),
        "section_started_at": attempt.section_started_at,
        "section_deadline_at": attempt.section_deadline_at,
        "current_section": attempt.current_section,
        "current_order": attempt.current_order,
        "current_task": current,
        "progress": {
            "completed": attempt.tasks.filter(
                state__in=[MockTaskState.SUBMITTED, MockTaskState.SKIPPED]
            ).count(),
            "total": attempt.tasks.count(),
        },
        "rules": exam_rules(attempt),
        "format": attempt.format_snapshot,
        "disclaimer": attempt.format_snapshot.get("limitation", LIMITATION),
    }
    if include_tasks:
        payload["tasks"] = [
            {
                "order": task.order,
                "section": task.section,
                "task_type": task.task_type,
                "title": task.snapshot["title"],
                "state": task.state,
                "session_id": str(task.session_id),
                "kind": task_kind(task),
            }
            for task in attempt.tasks.all()
        ]
    return payload


def results_payload(attempt: MockAttempt) -> dict:
    if attempt.state != MockState.COMPLETED:
        raise ResultsEmbargoed("Mock results are released only after all four components finish.")
    components = []
    for skill in COMPONENT_ORDER:
        tasks = list(attempt.tasks.filter(section=skill).select_related("session"))
        if skill in (Skill.LISTENING, Skill.READING):
            # Simulated-unscored items stay indistinguishable to the learner
            # during the attempt but never contribute to raw accuracy.
            scored_tasks = [task for task in tasks if not task.is_simulated_unscored]
            results = ObjectiveResult.objects.filter(
                session_id__in=[task.session_id for task in scored_tasks]
            )
            correct = sum(result.raw_correct for result in results)
            possible = sum(result.raw_possible for result in results)
            components.append(
                {
                    "skill": skill,
                    "measure": "practice_accuracy",
                    "raw_correct": correct,
                    "raw_possible": possible,
                    "accuracy_percent": round(100 * correct / possible) if possible else None,
                    "items_attempted": len(tasks),
                    "items_scored": len(scored_tasks),
                }
            )
        else:
            feedback = AIFeedback.objects.filter(
                session_item__session_id__in=[task.session_id for task in tasks]
            )
            ranges = [
                (item.assessment["estimated_level_low"], item.assessment["estimated_level_high"])
                for item in feedback
            ]
            components.append(
                {
                    "skill": skill,
                    "measure": "ai_assisted_practice_estimate",
                    "feedback_ready": len(ranges),
                    "tasks_total": len(tasks),
                    "estimate_low": round(sum(low for low, _ in ranges) / len(ranges), 1)
                    if ranges
                    else None,
                    "estimate_high": round(sum(high for _, high in ranges) / len(ranges), 1)
                    if ranges
                    else None,
                }
            )
    return {
        "attempt_id": str(attempt.id),
        "completed_at": attempt.completed_at,
        "components": components,
        "overall_score": None,
        "disclaimer": (
            "Unofficial practice results only. Objective accuracy is not converted to a CELPIP "
            "level; AI-assisted ranges are not official ratings. Immigration decisions use "
            "official component results."
        ),
    }
