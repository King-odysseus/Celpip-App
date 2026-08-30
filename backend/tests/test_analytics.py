"""Completion history, analytics aggregates, and personalised recommendations."""
from datetime import timedelta
from uuid import uuid4

import pytest
from django.core.management import call_command
from django.utils import timezone

from apps.accounts.models import User
from apps.ai_services.models import AIFeedback, AIJob, AIJobKind, AIJobStatus
from apps.assessments.models import SessionItem
from apps.content.models import ContentVersion, Question, TaskType
from apps.learning.models import MistakeRecord, MistakeState

pytestmark = pytest.mark.django_db

ME = "/api/v1/me"


@pytest.fixture
def learner(api_client):
    user = User.objects.create_user(identifier="analytics-learner", password="secret1")
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


def _submit_writing(api_client, django_capture_on_commit_callbacks):
    started = api_client.post(
        "/api/v1/sessions/",
        {
            "content_slug": "email-noisy-renovation",
            "mode": "practice",
            "time_limit_seconds": 600,
        },
        format="json",
    )
    assert started.status_code == 201
    session_id = started.json()["id"]
    with django_capture_on_commit_callbacks(execute=True):
        submitted = api_client.post(
            f"/api/v1/sessions/{session_id}/writing/submit/",
            {"text": "A complete practice writing response with enough words to be accepted."},
            format="json",
        )
    assert submitted.status_code == 200
    return session_id


def _attach_feedback(session_id: str, *, low: int = 6, high: int = 8) -> None:
    item = SessionItem.objects.get(session_id=session_id)
    job = AIJob.objects.create(
        kind=AIJobKind.WRITING_FEEDBACK,
        status=AIJobStatus.SUCCEEDED,
        session_item=item,
        provider="test-provider",
        model="test-model",
        prompt_version="1",
        run_after=timezone.now(),
    )
    AIFeedback.objects.create(
        session_item=item,
        job=job,
        kind=job.kind,
        provider="test-provider",
        model="test-model",
        prompt_version="1",
        assessment={
            "estimated_level_low": low,
            "estimated_level_high": high,
            "dimensions": [],
            "overall_summary": "",
            "strengths": [],
            "priorities": [],
            "confidence": "high",
            "disclaimer": "",
        },
    )


def test_analytics_endpoints_require_an_account(api_client):
    for path in (f"{ME}/analytics/", f"{ME}/history/", f"{ME}/recommendation/"):
        assert api_client.get(path).status_code == 401


def test_history_records_objective_completion(api_client, learner, django_capture_on_commit_callbacks):
    call_command("seed_reading_content", verbosity=0)
    _reading_attempt(api_client, django_capture_on_commit_callbacks, correct=True)

    payload = api_client.get(f"{ME}/history/").json()
    assert payload["count"] == 1
    entry = payload["results"][0]
    assert entry["kind"] == "objective"
    assert entry["skill"] == "reading"
    assert entry["task_type"]
    assert entry["title"]
    assert entry["measure"] == "accuracy_percent"
    assert entry["value"] == 100
    assert entry["label"] == "Practice accuracy"
    assert entry["destination"] == "/practice"
    assert entry["date"]


def test_history_tracks_writing_until_feedback_ready(
    api_client, learner, django_capture_on_commit_callbacks
):
    call_command("seed_writing_content", verbosity=0)
    session_id = _submit_writing(api_client, django_capture_on_commit_callbacks)

    entry = api_client.get(f"{ME}/history/").json()["results"][0]
    assert entry["kind"] == "writing"
    assert entry["measure"] == "awaiting_feedback"
    assert entry["value"] is None
    assert entry["label"] == "Awaiting AI analysis"

    _attach_feedback(session_id)
    entry = api_client.get(f"{ME}/history/").json()["results"][0]
    assert entry["measure"] == "estimated_midpoint"
    assert entry["value"] == 7.0
    assert entry["label"] == "AI-assisted practice estimate"


def test_history_paginates_and_rejects_bad_params(
    api_client, learner, django_capture_on_commit_callbacks
):
    call_command("seed_reading_content", verbosity=0)
    _reading_attempt(api_client, django_capture_on_commit_callbacks, correct=False)
    _reading_attempt(api_client, django_capture_on_commit_callbacks, correct=True)

    full = api_client.get(f"{ME}/history/").json()
    assert full["count"] == 2
    page_two = api_client.get(f"{ME}/history/?page_size=1&page=2").json()
    assert len(page_two["results"]) == 1
    assert page_two["count"] == 2

    for query in ("page_size=0", "page_size=abc", "page=-1"):
        response = api_client.get(f"{ME}/history/?{query}")
        assert response.status_code == 400
        assert response.json()["code"] == "invalid_query"


def test_analytics_aggregates_scores_and_mistakes(
    api_client, learner, django_capture_on_commit_callbacks
):
    call_command("seed_reading_content", verbosity=0)
    _reading_attempt(api_client, django_capture_on_commit_callbacks, correct=False)

    payload = api_client.get(f"{ME}/analytics/").json()
    assert len(payload["skills"]) == 4
    reading = next(item for item in payload["skills"] if item["skill"] == "reading")
    assert reading["attempts"] == 1
    assert reading["accuracy_percent"] is not None
    assert payload["mistakes"]["open_total"] == 1
    assert payload["mistakes"]["by_skill"][0]["skill"] == "reading"
    assert payload["history"][0]["kind"] == "objective"
    assert payload["disclaimer"]


def test_recommendation_points_at_weakest_skill(
    api_client, learner, django_capture_on_commit_callbacks
):
    call_command("seed_reading_content", verbosity=0)
    call_command("seed_listening_content", verbosity=0)
    _reading_attempt(api_client, django_capture_on_commit_callbacks, correct=True)

    payload = api_client.get(f"{ME}/recommendation/").json()
    recommendation = payload["recommendation"]
    assert recommendation is not None
    priorities = payload["basis"]["skill_priorities"]
    weakest = max(priorities, key=lambda skill: priorities[skill])
    assert recommendation["skill"] == weakest
    assert recommendation["launch_url"] == {
        "listening": "/practice/listening",
        "reading": "/practice",
        "writing": "/practice/writing",
        "speaking": "/practice/speaking",
    }[weakest]
    assert recommendation["content_slug"]
    assert recommendation["difficulty"] in (1, 2, 3)
    assert recommendation["reason"]
    assert payload["basis"]["selected_task_type"]
    assert payload["disclaimer"]


def test_recommendation_prefers_task_family_with_open_mistakes(api_client, learner):
    call_command("seed_listening_content", verbosity=0)
    target = (
        TaskType.objects.filter(skill="listening", is_active=True)
        .order_by("part_number")
        .first()
    )
    question = Question.objects.filter(content_version__item__task_type=target).first()
    MistakeRecord.objects.create(
        user=learner,
        question=question,
        skill="listening",
        task_type=target,
        stem_snapshot="Stem",
        selected_snapshot="A",
        correct_snapshot="B",
        explanation_snapshot="Because the text says so.",
        occurrences=2,
        state=MistakeState.OPEN,
        first_seen_at=timezone.now(),
        last_seen_at=timezone.now(),
    )

    payload = api_client.get(f"{ME}/recommendation/").json()
    recommendation = payload["recommendation"]
    assert recommendation is not None
    assert recommendation["task_type"] == target.code
    assert "open mistake pattern" in recommendation["reason"]


def test_recommendation_without_published_content_is_null(api_client, learner):
    payload = api_client.get(f"{ME}/recommendation/").json()
    assert payload["recommendation"] is None
    assert "No active task families" in payload["basis"]["reasoning"]
    assert payload["disclaimer"]
