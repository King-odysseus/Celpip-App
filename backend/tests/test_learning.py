"""Authenticated progress, repeat mistakes, and explainable study plans."""

from datetime import timedelta
from io import StringIO
from uuid import uuid4

import pytest
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.utils import timezone

from apps.accounts.models import LearnerProfile, User
from apps.content.models import ContentVersion
from apps.learning.models import MistakeRecord, MistakeState, StudyPlan, StudyTaskState
from apps.learning.services import regenerate_plan

pytestmark = pytest.mark.django_db


@pytest.fixture
def learner(api_client):
    user = User.objects.create_user(identifier="progress-learner", password="secret1")
    api_client.force_authenticate(user)
    return user


def _reading_attempt(api_client, django_capture_on_commit_callbacks, *, correct: bool):
    version = ContentVersion.objects.get(item__slug="garden-plot-renewal", status="published")
    started = api_client.post(
        "/api/v1/sessions/",
        {
            "content_slug": "garden-plot-renewal",
            "mode": "practice",
            "time_limit_seconds": 600,
        },
        format="json",
    )
    assert started.status_code == 201
    session_id = started.json()["id"]
    for index, question in enumerate(version.questions.prefetch_related("choices")):
        choices = list(question.choices.all())
        answer = next(choice for choice in choices if choice.is_correct)
        if index == 0 and not correct:
            answer = next(choice for choice in choices if not choice.is_correct)
        saved = api_client.put(
            f"/api/v1/sessions/{session_id}/responses/{question.pk}/",
            {"selected_choice_id": answer.pk, "expected_revision": 0},
            format="json",
            HTTP_IDEMPOTENCY_KEY=str(uuid4()),
        )
        assert saved.status_code == 200
    with django_capture_on_commit_callbacks(execute=True):
        submitted = api_client.post(f"/api/v1/sessions/{session_id}/submit/")
    assert submitted.status_code == 200
    return submitted.json()


def test_learning_endpoints_require_an_account(api_client):
    for path in ("/api/v1/me/progress/", "/api/v1/me/mistakes/", "/api/v1/me/study-plan/"):
        assert api_client.get(path).status_code == 401


def test_repeated_mistake_merges_then_correct_retry_resolves(
    api_client, learner, django_capture_on_commit_callbacks
):
    call_command("seed_reading_content", verbosity=0, stdout=StringIO())
    _reading_attempt(api_client, django_capture_on_commit_callbacks, correct=False)
    _reading_attempt(api_client, django_capture_on_commit_callbacks, correct=False)

    mistake = MistakeRecord.objects.get(user=learner)
    assert mistake.occurrences == 2
    assert mistake.state == MistakeState.OPEN
    listing = api_client.get("/api/v1/me/mistakes/?state=open")
    assert listing.status_code == 200
    assert listing.json()["results"][0]["selected"]
    assert listing.json()["results"][0]["correct"]

    _reading_attempt(api_client, django_capture_on_commit_callbacks, correct=True)
    mistake.refresh_from_db()
    assert mistake.state == MistakeState.RESOLVED
    assert mistake.resolved_at is not None


def test_progress_keeps_accuracy_separate_from_constructed_estimates(
    api_client, learner, django_capture_on_commit_callbacks
):
    call_command("seed_reading_content", verbosity=0, stdout=StringIO())
    result = _reading_attempt(api_client, django_capture_on_commit_callbacks, correct=False)
    payload = api_client.get("/api/v1/me/progress/").json()
    reading = next(item for item in payload["skills"] if item["skill"] == "reading")

    assert reading["attempts"] == 1
    assert reading["accuracy_percent"] == result["accuracy_percent"]
    assert reading["estimate_low"] is None
    assert payload["overall_readiness"] is None
    assert "withheld" in payload["readiness_explanation"]
    assert payload["coverage"] == {"practised_skills": 1, "total_skills": 4}


def test_plan_rotates_every_available_skill_and_versions_explanations(learner):
    call_command("seed_reading_content", verbosity=0, stdout=StringIO())
    call_command("seed_listening_content", verbosity=0, stdout=StringIO())
    call_command("seed_writing_content", verbosity=0, stdout=StringIO())
    call_command("seed_speaking_content", verbosity=0, stdout=StringIO())

    first = regenerate_plan(learner)
    skills = set(first.tasks.values_list("skill", flat=True))
    assert skills == {"listening", "reading", "writing", "speaking"}
    assert "rule" in first.reason_summary
    assert all(task.reason for task in first.tasks.all())

    second = regenerate_plan(learner)
    first.refresh_from_db()
    assert first.is_active is False
    assert second.version == first.version + 1
    assert StudyPlan.objects.filter(user=learner, is_active=True).count() == 1


def test_plan_includes_all_four_skills_on_each_study_day(learner):
    _all_skill_task_types()

    plan = regenerate_plan(learner)

    for date in set(plan.tasks.values_list("scheduled_date", flat=True)):
        assert set(plan.tasks.filter(scheduled_date=date).values_list("skill", flat=True)) == {
            "listening",
            "reading",
            "writing",
            "speaking",
        }


def test_plan_runs_through_a_future_exam_date(learner):
    _all_skill_task_types()
    profile, _ = LearnerProfile.objects.get_or_create(user=learner)
    exam_date = timezone.localdate() + timedelta(days=40)
    profile.exam_date = exam_date
    profile.save(update_fields=["exam_date"])

    plan = regenerate_plan(learner)

    scheduled_dates = list(plan.tasks.values_list("scheduled_date", flat=True))
    assert scheduled_dates
    assert max(scheduled_dates) <= exam_date
    assert max(scheduled_dates).month == exam_date.month


def test_plan_task_completion_is_owned_and_generated_details_are_immutable(api_client, learner):
    call_command("seed_reading_content", verbosity=0, stdout=StringIO())
    plan = regenerate_plan(learner)
    task = plan.tasks.first()
    response = api_client.patch(
        f"/api/v1/me/study-plan/tasks/{task.pk}/",
        {"state": "completed"},
        format="json",
    )
    assert response.status_code == 200
    assert response.json()["completed_at"]
    task.refresh_from_db()
    task.title = "Tampered title"
    with pytest.raises(ValidationError, match="immutable"):
        task.save()

    stranger = User.objects.create_user(identifier="plan-stranger", password="secret1")
    api_client.force_authenticate(stranger)
    assert (
        api_client.patch(
            f"/api/v1/me/study-plan/tasks/{task.pk}/",
            {"state": "skipped"},
            format="json",
        ).status_code
        == 404
    )


def _all_skill_task_types() -> None:
    """Minimal task types so the rotation spans all four skills (no audio)."""
    from apps.content.models import Skill, TaskType

    for index, skill in enumerate(Skill.values):
        TaskType.objects.create(
            code=f"tt_{skill}", skill=skill, title=skill.capitalize(),
            part_number=index + 1, description="", strategy=[], common_mistakes=[],
        )


def test_plan_completions_survive_auto_regeneration(learner):
    _all_skill_task_types()
    first = regenerate_plan(learner)
    target = first.tasks.first()
    target.state = StudyTaskState.COMPLETED
    target.completed_at = timezone.now()
    target.save(update_fields=["state", "completed_at"])

    # Auto-regeneration runs after every practice submission; the manual
    # completion must map onto the regenerated schedule, keyed by date+skill.
    second = regenerate_plan(learner)
    carried = second.tasks.get(scheduled_date=target.scheduled_date, skill=target.skill)
    assert carried.state == StudyTaskState.COMPLETED
    assert carried.completed_at is not None

    # A fresh (never-before-scheduled) task stays pending.
    assert second.tasks.exclude(pk=carried.pk).filter(state=StudyTaskState.COMPLETED).count() == 0


def test_plan_name_persists_across_regeneration(learner):
    call_command("seed_reading_content", verbosity=0, stdout=StringIO())
    first = regenerate_plan(learner)
    first.name = "Countdown push"
    first.save(update_fields=["name"])

    second = regenerate_plan(learner)
    assert second.name == "Countdown push"
    assert StudyPlan.objects.filter(user=learner, is_active=True).get().name == "Countdown push"


def test_adaptive_plan_graduates_difficulty_and_preference_can_be_fixed(api_client, learner):
    _all_skill_task_types()
    plan = regenerate_plan(learner)
    reading = list(plan.tasks.filter(skill="reading").order_by("scheduled_date"))
    assert "difficulty=1" in reading[0].destination
    assert any("difficulty=2" in task.destination for task in reading[3:])
    assert any("difficulty=3" in task.destination for task in reading[6:])

    changed = api_client.patch(
        "/api/v1/me/study-plan/",
        {"difficulty_preference": "challenge"},
        format="json",
    )
    assert changed.status_code == 200
    payload = changed.json()
    assert payload["difficulty_preference"] == "challenge"
    assert all("difficulty=3" in task["destination"] for task in payload["tasks"])


def test_completed_lesson_history_survives_regeneration(api_client, learner):
    call_command("seed_reading_content", verbosity=0, stdout=StringIO())
    first = regenerate_plan(learner)
    task = first.tasks.exclude(destination__contains="lesson=").first()
    if task is None:
        task = first.tasks.first()
    # Use a concrete historical destination to model a lesson completed from a plan.
    version = ContentVersion.objects.filter(item__task_type=task.task_type, status="published").first()
    assert version is not None
    StudyTask = type(task)
    StudyTask.objects.filter(pk=task.pk).update(
        destination=f"/practice?difficulty=1&lesson={version.item.slug}",
        state=StudyTaskState.COMPLETED,
        completed_at=timezone.now(),
    )

    regenerate_plan(learner)
    payload = api_client.get("/api/v1/me/study-plan/").json()
    assert version.item.slug in payload["completed_lessons"]

    # The historical task remains completable even after its plan is inactive.
    response = api_client.patch(
        f"/api/v1/me/study-plan/tasks/{task.pk}/",
        {"state": "completed"},
        format="json",
    )
    assert response.status_code == 200


def test_plan_name_patch_and_consistency_payload(api_client, learner):
    call_command("seed_reading_content", verbosity=0, stdout=StringIO())
    plan = regenerate_plan(learner)
    target = plan.tasks.first()
    target.state = StudyTaskState.COMPLETED
    target.completed_at = timezone.now()
    target.save(update_fields=["state", "completed_at"])

    renamed = api_client.patch("/api/v1/me/study-plan/", {"name": "My Plan"}, format="json")
    assert renamed.status_code == 200
    payload = renamed.json()
    assert payload["name"] == "My Plan"
    assert "id" in payload and "version" in payload

    consistency = payload["consistency"]
    assert consistency["streak"]["days"] >= 1
    assert len(consistency["days"]) == consistency["window_days"]
    completed_day = next(day for day in consistency["days"] if day["completed"])
    assert completed_day["skills"][target.skill] is True

    # The renamed plan is what the next GET returns, and regeneration keeps it.
    listing = api_client.get("/api/v1/me/study-plan/")
    assert listing.status_code == 200
    assert listing.json()["name"] == "My Plan"
    assert regenerate_plan(learner).name == "My Plan"


def test_manual_mistake_resolution_is_owner_scoped(
    api_client, learner, django_capture_on_commit_callbacks
):
    call_command("seed_reading_content", verbosity=0, stdout=StringIO())
    _reading_attempt(api_client, django_capture_on_commit_callbacks, correct=False)
    mistake = MistakeRecord.objects.get(user=learner)
    response = api_client.patch(
        f"/api/v1/me/mistakes/{mistake.pk}/",
        {"state": "resolved"},
        format="json",
    )
    assert response.status_code == 200
    assert response.json()["state"] == "resolved"
    assert response.json()["resolved_at"]
