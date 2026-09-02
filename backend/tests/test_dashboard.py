"""Authenticated dashboard: aggregation, streak, signals, readiness, ordering."""
from __future__ import annotations

import itertools
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from django.utils import timezone

from apps.accounts.models import LearnerProfile, User
from apps.ai_services.models import AIFeedback, AIJob, AIJobKind, AIJobStatus
from apps.assessments.models import (
    AssessmentSession,
    ObjectiveResult,
    SessionItem,
)
from apps.content.models import ContentItem, ContentVersion, PublicationStatus, Skill, TaskType
from apps.learning.models import StudyPlan, StudyTask
from apps.learning.services import (
    READINESS_FORMULA,
    _activity_dates,
    _readiness_indicator,
    dashboard_payload,
    study_streak,
)

pytestmark = pytest.mark.django_db

_counter = itertools.count()


def _make_user(identifier: str = "dash-learner", tz: str = "America/Toronto"):
    user = User.objects.create_user(identifier=identifier, password="secret1")
    profile, _ = LearnerProfile.objects.get_or_create(user=user)
    profile.timezone = tz
    profile.save(update_fields=["timezone"])
    return user, profile


def _task_type(*, skill: str, title: str = "Practice prompt") -> TaskType:
    code = f"task_{next(_counter)}"
    part_number = next(_counter) + 1
    return TaskType.objects.create(
        code=code,
        skill=skill,
        title=title,
        part_number=part_number,
        description="",
        strategy=[],
        common_mistakes=[],
    )


def _content_version(
    *, skill: str, title: str = "Practice prompt"
) -> tuple[TaskType, ContentVersion]:
    task_type = _task_type(skill=skill, title=title)
    item = ContentItem.objects.create(
        slug=f"slug-{next(_counter)}",
        task_type=task_type,
        title=title,
        topic="t",
        difficulty=1,
        estimated_level=5,
        provenance="t",
    )
    version = ContentVersion.objects.create(
        item=item,
        version=1,
        status=PublicationStatus.PUBLISHED,
        instructions="",
        stimulus={},
    )
    return task_type, version


def _objective_result(
    user, *, skill: str, raw_correct: int, raw_possible: int, scored_at, title: str = "Prompt"
) -> ObjectiveResult:
    task_type, version = _content_version(skill=skill, title=title)
    session = AssessmentSession.objects.create(user=user, mode="practice", state="submitted")
    SessionItem.objects.create(
        session=session,
        content_version=version,
        order=1,
        snapshot={"skill": skill, "task_type": task_type.code, "title": title},
    )
    result = ObjectiveResult.objects.create(
        session=session,
        raw_correct=raw_correct,
        raw_possible=raw_possible,
        outcomes=[],
    )
    ObjectiveResult.objects.filter(pk=result.pk).update(scored_at=scored_at)
    return result


def _feedback(
    user, *, skill: str, low: int, high: int, created_at, title: str = "Prompt"
) -> AIFeedback:
    task_type, version = _content_version(skill=skill, title=title)
    session = AssessmentSession.objects.create(user=user, mode="practice", state="submitted")
    item = SessionItem.objects.create(
        session=session,
        content_version=version,
        order=1,
        snapshot={"skill": skill, "task_type": task_type.code, "title": title},
    )
    job = AIJob.objects.create(
        kind=AIJobKind.WRITING_FEEDBACK,
        status=AIJobStatus.SUCCEEDED,
        session_item=item,
        provider="fake",
        model="m",
        prompt_version="v",
        run_after=created_at,
    )
    feedback = AIFeedback.objects.create(
        session_item=item,
        job=job,
        kind=AIJobKind.WRITING_FEEDBACK,
        provider="fake",
        model="m",
        prompt_version="v",
        assessment={"estimated_level_low": low, "estimated_level_high": high},
    )
    AIFeedback.objects.filter(pk=feedback.pk).update(created_at=created_at)
    return feedback


def _submitted_constructed_session(
    user, *, skill: str, job_status=None, state: str = "submitted"
) -> AssessmentSession:
    """A submitted Writing/Speaking session with no AIFeedback artifact.

    ``job_status`` optionally attaches a queued/running/failed AI job to the
    session item so tests can prove queued/failed feedback still counts as a
    completed attempt without producing a performance signal.
    """
    task_type, version = _content_version(skill=skill, title="Prompt")
    session = AssessmentSession.objects.create(user=user, mode="practice", state=state)
    item = SessionItem.objects.create(
        session=session,
        content_version=version,
        order=1,
        snapshot={"skill": skill, "task_type": task_type.code, "title": "Prompt"},
    )
    if job_status is not None:
        AIJob.objects.create(
            kind=(
                AIJobKind.WRITING_FEEDBACK
                if skill == Skill.WRITING
                else AIJobKind.SPEAKING_FEEDBACK
            ),
            status=job_status,
            session_item=item,
            provider="fake",
            model="m",
            prompt_version="v",
            run_after=timezone.now(),
        )
    return session


# ── Streak rule ─────────────────────────────────────────────────────────────


def test_study_streak_anchors_today_when_active_today():
    today = date(2026, 8, 29)
    streak = study_streak({today, today - timedelta(days=1), today - timedelta(days=2)}, today)
    assert streak == {
        "days": 3, "active_today": True, "anchor": "today",
        "at_risk": False, "grace_days_remaining": None,
    }


def test_study_streak_anchors_yesterday_when_today_inactive():
    today = date(2026, 8, 29)
    yesterday = today - timedelta(days=1)
    streak = study_streak({yesterday, yesterday - timedelta(days=1)}, today)
    assert streak == {
        "days": 2, "active_today": False, "anchor": "yesterday",
        "at_risk": True, "grace_days_remaining": 1,
    }


def test_study_streak_ignores_future_dates():
    today = date(2026, 8, 29)
    future = today + timedelta(days=1)
    assert study_streak({today, future}, today)["days"] == 1


def test_study_streak_breaks_on_gap():
    today = date(2026, 8, 29)
    dates = {today, today - timedelta(days=1), today - timedelta(days=3)}
    assert study_streak(dates, today)["days"] == 2


def test_study_streak_survives_a_two_day_grace_window():
    """Missing up to STREAK_GRACE_DAYS (2) consecutive days does not reset the
    streak, but the learner is flagged at_risk with a countdown so the UI can
    remind them before it's too late."""
    today = date(2026, 8, 29)

    one_day_missed = study_streak({today - timedelta(days=1)}, today)
    assert one_day_missed["days"] == 1
    assert one_day_missed["at_risk"] is True
    assert one_day_missed["grace_days_remaining"] == 1

    two_days_missed = study_streak({today - timedelta(days=2)}, today)
    assert two_days_missed["days"] == 1
    assert two_days_missed["at_risk"] is True
    assert two_days_missed["grace_days_remaining"] == 0  # last chance today


def test_study_streak_zero_when_no_recent_activity():
    today = date(2026, 8, 29)
    # A third consecutive missed day is outside the 2-day grace window.
    assert study_streak({today - timedelta(days=3)}, today)["days"] == 0
    assert study_streak(set(), today)["days"] == 0


def test_activity_dates_use_profile_timezone_across_day_boundary():
    user, _ = _make_user(tz="America/Toronto")
    # 03:00 UTC is still the previous evening in Toronto (UTC-4 in summer).
    _objective_result(
        user,
        skill=Skill.READING,
        raw_correct=1,
        raw_possible=1,
        scored_at=datetime(2026, 8, 29, 3, 0, tzinfo=UTC),
        title="Late night",
    )
    # 05:00 UTC is 01:00 local, so already the next calendar day.
    _objective_result(
        user,
        skill=Skill.READING,
        raw_correct=1,
        raw_possible=1,
        scored_at=datetime(2026, 8, 29, 5, 0, tzinfo=UTC),
        title="Early morning",
    )
    assert _activity_dates(user, ZoneInfo("America/Toronto")) == {
        date(2026, 8, 28),
        date(2026, 8, 29),
    }


# ── Endpoint ────────────────────────────────────────────────────────────────


def test_dashboard_requires_an_account(api_client):
    assert api_client.get("/api/v1/me/dashboard/").status_code == 401


def test_dashboard_is_owner_scoped(api_client):
    learner, _ = _make_user(identifier="owner")
    other, _ = _make_user(identifier="other")
    _objective_result(
        learner,
        skill=Skill.READING,
        raw_correct=3,
        raw_possible=4,
        scored_at=timezone.now(),
    )
    _submitted_constructed_session(learner, skill=Skill.WRITING)
    api_client.force_authenticate(other)
    response = api_client.get("/api/v1/me/dashboard/")
    assert response.status_code == 200
    payload = response.json()
    assert payload["totals"] == {"objective_questions_completed": 0, "completed_attempts": 0}
    assert payload["recent_results"] == []


# ── Aggregation and signals ─────────────────────────────────────────────────


def test_dashboard_empty_evidence_state():
    user, _ = _make_user()
    payload = dashboard_payload(user)

    assert payload["totals"] == {"objective_questions_completed": 0, "completed_attempts": 0}
    assert payload["streak"]["days"] == 0
    assert payload["streak"]["active_today"] is False
    assert payload["recent_results"] == []
    assert payload["coverage"] == {"practised_skills": 0, "total_skills": 4}

    assert payload["signals"]["strongest"] is None
    assert payload["signals"]["needs_attention"]["skill"] == Skill.LISTENING
    assert payload["signals"]["needs_attention"]["basis"] == "No practice recorded yet"

    assert payload["readiness"]["state"] == "insufficient_evidence"
    assert payload["readiness"]["indicator"] is None
    assert payload["readiness"]["is_official"] is False


def test_dashboard_partial_evidence_readiness_and_totals():
    user, _ = _make_user()
    _objective_result(
        user,
        skill=Skill.READING,
        raw_correct=3,
        raw_possible=4,
        scored_at=timezone.now(),
    )
    payload = dashboard_payload(user)

    assert payload["totals"]["objective_questions_completed"] == 4
    assert payload["totals"]["completed_attempts"] == 1
    assert payload["coverage"] == {"practised_skills": 1, "total_skills": 4}

    assert payload["signals"]["strongest"]["skill"] == Skill.READING
    assert payload["signals"]["strongest"]["measure"] == "accuracy_percent"
    assert payload["signals"]["strongest"]["value"] == 75
    # Unpractised skills rank first for needs-attention, never scored zero.
    assert payload["signals"]["needs_attention"]["skill"] == Skill.LISTENING
    assert payload["signals"]["needs_attention"]["planning_signal"] is None

    assert payload["readiness"]["state"] == "estimated"
    assert isinstance(payload["readiness"]["indicator"], int)


def test_dashboard_full_evidence_signals():
    user, _ = _make_user()
    _objective_result(
        user, skill=Skill.LISTENING, raw_correct=4, raw_possible=5, scored_at=timezone.now()
    )
    _objective_result(
        user, skill=Skill.READING, raw_correct=3, raw_possible=5, scored_at=timezone.now()
    )
    _feedback(user, skill=Skill.WRITING, low=6, high=8, created_at=timezone.now())
    _feedback(user, skill=Skill.SPEAKING, low=5, high=7, created_at=timezone.now())

    payload = dashboard_payload(user)

    assert payload["totals"] == {"objective_questions_completed": 10, "completed_attempts": 4}
    assert payload["coverage"] == {"practised_skills": 4, "total_skills": 4}

    strongest, needs_attention = (
        payload["signals"]["strongest"],
        payload["signals"]["needs_attention"],
    )
    # Listening 80% > Reading 60% > Writing 58 > Speaking 50.
    assert strongest["skill"] == Skill.LISTENING
    assert strongest["planning_signal"] == 80
    assert needs_attention["skill"] == Skill.SPEAKING
    assert needs_attention["measure"] == "estimated_midpoint"
    assert needs_attention["planning_signal"] == 50
    assert "unofficial" in payload["signals"]["note"]


def test_dashboard_counts_submitted_writing_and_speaking_without_feedback():
    user, _ = _make_user()
    _submitted_constructed_session(user, skill=Skill.WRITING)
    _submitted_constructed_session(user, skill=Skill.SPEAKING)

    payload = dashboard_payload(user)

    assert payload["totals"]["objective_questions_completed"] == 0
    assert payload["totals"]["completed_attempts"] == 2

    # Volume counts both completed attempts, but no evidence exists yet for
    # coverage/performance.
    by_key = {component["key"]: component for component in payload["readiness"]["components"]}
    assert by_key["volume"]["value"] == 20
    assert by_key["volume"]["raw"] == "2 completed attempt(s)"
    assert by_key["performance"]["value"] == 0
    assert payload["coverage"] == {"practised_skills": 0, "total_skills": 4}
    assert payload["signals"]["strongest"] is None
    assert payload["readiness"]["state"] == "estimated"


def test_dashboard_queued_and_failed_feedback_count_attempts_without_performance():
    user, _ = _make_user()
    _submitted_constructed_session(user, skill=Skill.WRITING, job_status=AIJobStatus.QUEUED)
    _submitted_constructed_session(user, skill=Skill.SPEAKING, job_status=AIJobStatus.FAILED)

    payload = dashboard_payload(user)

    assert payload["totals"]["completed_attempts"] == 2
    by_key = {component["key"]: component for component in payload["readiness"]["components"]}
    assert by_key["volume"]["value"] == 20
    assert by_key["performance"]["value"] == 0
    assert payload["coverage"] == {"practised_skills": 0, "total_skills": 4}


def test_dashboard_excludes_active_sessions_from_completed_attempts():
    user, _ = _make_user()
    _objective_result(
        user, skill=Skill.READING, raw_correct=2, raw_possible=2, scored_at=timezone.now()
    )
    _submitted_constructed_session(user, skill=Skill.WRITING, state="active")

    payload = dashboard_payload(user)

    # Only the submitted reading session counts; the active writing session does not.
    assert payload["totals"]["completed_attempts"] == 1
    by_key = {component["key"]: component for component in payload["readiness"]["components"]}
    assert by_key["volume"]["value"] == 10


# ── Recent results ordering and limit ───────────────────────────────────────


def test_recent_results_are_newest_first_and_limited():
    user, _ = _make_user()
    base = datetime(2026, 8, 29, 12, 0, tzinfo=UTC)
    for index in range(7):
        _objective_result(
            user,
            skill=Skill.READING,
            raw_correct=index,
            raw_possible=10,
            scored_at=base - timedelta(hours=index),
            title=f"Prompt {index}",
        )
    payload = dashboard_payload(user)
    results = payload["recent_results"]
    assert len(results) == 5
    # Newest first: index 0 is the most recent, so titles run 0..4.
    assert [item["title"] for item in results] == [
        "Prompt 0",
        "Prompt 1",
        "Prompt 2",
        "Prompt 3",
        "Prompt 4",
    ]


def test_recent_results_include_feedback_and_are_privacy_safe():
    user, _ = _make_user()
    _feedback(
        user,
        skill=Skill.WRITING,
        low=6,
        high=8,
        created_at=datetime(2026, 8, 29, 12, 0, tzinfo=UTC),
        title="Survey",
    )
    payload = dashboard_payload(user)
    result = payload["recent_results"][0]
    assert result["skill"] == Skill.WRITING
    assert result["measure"] == "estimated_midpoint"
    assert result["value"] == 7.0
    assert result["destination"] == "/practice/writing"
    # No prompt text, transcripts, or raw responses may leak.
    for key in ("stem", "text", "transcript", "outcomes", "snapshot"):
        assert key not in result


# ── Readiness formula ───────────────────────────────────────────────────────


def _skill_summary(skill, *, attempts, accuracy=None, estimate_low=None, estimate_high=None):
    return {
        "skill": skill,
        "attempts": attempts,
        "questions_total": 0,
        "accuracy_percent": accuracy,
        "estimate_low": estimate_low,
        "estimate_high": estimate_high,
    }


def test_readiness_formula_is_deterministic_and_documented():
    skills = [
        _skill_summary(Skill.LISTENING, attempts=0),
        _skill_summary(Skill.READING, attempts=2, accuracy=62),
        _skill_summary(Skill.WRITING, attempts=1, estimate_low=6, estimate_high=6),
        _skill_summary(Skill.SPEAKING, attempts=0),
    ]
    today = date(2026, 8, 29)
    indicator = _readiness_indicator(skills, {today}, today, completed_attempts=3)

    assert indicator["formula"] == READINESS_FORMULA
    assert indicator["state"] == "estimated"
    assert round(sum(component["weight"] for component in indicator["components"]), 6) == 1.0

    by_key = {component["key"]: component for component in indicator["components"]}
    assert by_key["coverage"]["value"] == 50
    assert by_key["recency"]["value"] == 100
    assert by_key["volume"]["value"] == 30
    assert by_key["performance"]["value"] == 56
    # 0.30*50 + 0.25*100 + 0.25*30 + 0.20*56 = 58.7 -> 59
    assert indicator["indicator"] == 59


def test_readiness_recency_decays_per_day():
    skills = [_skill_summary(Skill.READING, attempts=1, accuracy=100)]
    today = date(2026, 8, 29)
    # Three days since the most recent activity.
    indicator = _readiness_indicator(
        skills, {today - timedelta(days=3)}, today, completed_attempts=1
    )
    by_key = {component["key"]: component for component in indicator["components"]}
    assert by_key["recency"]["value"] == 70


# ── Today's tasks and next upcoming ─────────────────────────────────────────


def test_today_and_next_are_timezone_driven():
    user, profile = _make_user(tz="America/Toronto")
    zone = ZoneInfo(profile.timezone)
    today = timezone.now().astimezone(zone).date()
    tomorrow = today + timedelta(days=1)

    plan = StudyPlan.objects.create(user=user, version=1, is_active=True, reason_summary={})
    task_type = _task_type(skill=Skill.READING)
    StudyTask.objects.create(
        plan=plan, scheduled_date=today, order=1, skill=Skill.READING,
        task_type=task_type, title="Today", minutes=10, reason="r",
        destination="/practice", state="pending",
    )
    StudyTask.objects.create(
        plan=plan, scheduled_date=tomorrow, order=2, skill=Skill.READING,
        task_type=task_type, title="Tomorrow", minutes=10, reason="r",
        destination="/practice", state="pending",
    )

    payload = dashboard_payload(user)
    assert payload["today"]["date"] == today.isoformat()
    assert payload["today"]["timezone"] == "America/Toronto"
    assert [task["title"] for task in payload["today"]["tasks"]] == ["Today"]
    assert payload["next_upcoming_task"]["title"] == "Tomorrow"


def test_today_and_next_are_empty_without_a_plan():
    user, _ = _make_user()
    payload = dashboard_payload(user)
    assert payload["today"]["tasks"] == []
    assert payload["next_upcoming_task"] is None
