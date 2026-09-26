"""Provider contracts, audited jobs, feedback privacy, and draft review gates."""

from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.utils import timezone

from apps.accounts.models import User
from apps.ai_services.contracts import ProviderError, ProviderResult
from apps.ai_services.models import AICoachMessage, AIFeedback, AIJob, AIJobKind, AIJobStatus
from apps.ai_services.providers import FakeProvider, OpenAIProvider
from apps.ai_services.services import (
    FEEDBACK_RETENTION_DAYS,
    ask_coach,
    claim_next_job,
    coach_messages,
    enqueue_content_draft,
    enqueue_response_exemplar,
    feedback_history,
    materialize_content_draft,
    run_job,
)
from apps.ai_services.throttling import AICoachRateThrottle
from apps.assessments.models import (
    AssessmentSession,
    SessionItem,
    SpeakingSubmission,
    WritingSubmission,
)
from apps.assessments.storage import private_recording_storage
from apps.content.models import (
    ContentItem,
    ContentVersion,
    PublicationStatus,
    SourceType,
    TaskType,
)

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def isolated_recording_storage(tmp_path, monkeypatch):
    monkeypatch.setattr(private_recording_storage, "_location", str(tmp_path))
    private_recording_storage.__dict__.pop("base_location", None)
    private_recording_storage.__dict__.pop("location", None)


def _guest_headers(started):
    return {"HTTP_X_GUEST_TOKEN": started.json()["guest_token"]}


def _start(api_client, slug):
    return api_client.post(
        "/api/v1/sessions/",
        {"content_slug": slug, "mode": "practice", "time_limit_seconds": 600},
        format="json",
    )


def _submit_writing(api_client, django_capture_on_commit_callbacks):
    call_command("seed_writing_content", verbosity=0)
    started = _start(api_client, "email-noisy-renovation")
    session_id = started.json()["id"]
    with django_capture_on_commit_callbacks(execute=True):
        submitted = api_client.post(
            f"/api/v1/sessions/{session_id}/writing/submit/",
            {
                "text": (
                    "I am writing about the renovation noise. "
                    "Please limit work to daytime hours."
                )
            },
            format="json",
            **_guest_headers(started),
        )
    assert submitted.status_code == 200
    return started


def test_writing_submission_queues_runs_and_exposes_owned_feedback(
    api_client, django_capture_on_commit_callbacks
):
    started = _submit_writing(api_client, django_capture_on_commit_callbacks)
    job = AIJob.objects.get(kind=AIJobKind.WRITING_FEEDBACK)
    assert job.status == AIJobStatus.QUEUED
    assert job.prompt_version and job.input_snapshot["response"]

    claimed = claim_next_job()
    finished = run_job(claimed, provider=FakeProvider())
    assert finished.status == AIJobStatus.SUCCEEDED, (
        finished.error_code,
        finished.error_message,
    )
    feedback = AIFeedback.objects.get()
    assert feedback.assessment["estimated_level_low"] <= feedback.assessment["estimated_level_high"]
    assert "not an official CELPIP score" in feedback.assessment["disclaimer"]
    exemplar = enqueue_response_exemplar(finished.session_item)
    assert exemplar.input_snapshot["learner_response"] == (
        "I am writing about the renovation noise. Please limit work to daytime hours."
    )
    assert exemplar.input_snapshot["feedback"]["priorities"]

    endpoint = f"/api/v1/sessions/{started.json()['id']}/ai-feedback/"
    assert api_client.get(endpoint).status_code == 403
    owned = api_client.get(endpoint, **_guest_headers(started))
    assert owned.status_code == 200
    assert owned.json()["status"] == "succeeded"
    assert owned.json()["audit"]["prompt_version"] == job.prompt_version


def test_speaking_job_transcribes_private_recording(
    api_client, django_capture_on_commit_callbacks
):
    call_command("seed_speaking_content", verbosity=0)
    started = _start(api_client, "advice-first-canadian-winter")
    session_id = started.json()["id"]
    saved = api_client.put(
        f"/api/v1/sessions/{session_id}/speaking/",
        {
            "audio": SimpleUploadedFile(
                "response.webm", b"\x1aE\xdf\xa3practice-audio", content_type="audio/webm"
            ),
            "duration_ms": 1200,
            "expected_revision": 0,
        },
        format="multipart",
        HTTP_IDEMPOTENCY_KEY=str(uuid4()),
        **_guest_headers(started),
    )
    assert saved.status_code == 200
    with django_capture_on_commit_callbacks(execute=True):
        submitted = api_client.post(
            f"/api/v1/sessions/{session_id}/speaking/submit/",
            **_guest_headers(started),
        )
    assert submitted.status_code == 200

    job = claim_next_job()
    finished = run_job(job, provider=FakeProvider())
    assert finished.status == AIJobStatus.SUCCEEDED, (
        finished.error_code,
        finished.error_message,
    )
    feedback = AIFeedback.objects.get(kind=AIJobKind.SPEAKING_FEEDBACK)
    assert feedback.transcript.startswith("Development transcript")
    assert SpeakingSubmission.objects.get().audio.name not in str(job.input_snapshot)
    with pytest.raises(ValidationError, match="immutable"):
        feedback.save()


class MalformedProvider(FakeProvider):
    def evaluate_writing(self, payload: dict) -> ProviderResult:
        del payload
        return ProviderResult({"dimensions": []})


class FailingProvider(FakeProvider):
    def evaluate_writing(self, payload: dict) -> ProviderResult:
        del payload
        raise ProviderError("temporary", "Temporary safe failure.")


def test_malformed_output_fails_without_feedback(
    api_client, django_capture_on_commit_callbacks
):
    _submit_writing(api_client, django_capture_on_commit_callbacks)
    failed = run_job(claim_next_job(), provider=MalformedProvider())
    assert failed.status == AIJobStatus.FAILED
    assert failed.error_code == "invalid_output"
    assert not AIFeedback.objects.exists()


def test_retryable_provider_error_requeues_job(
    api_client, django_capture_on_commit_callbacks
):
    _submit_writing(api_client, django_capture_on_commit_callbacks)
    failed = run_job(claim_next_job(), provider=FailingProvider())
    assert failed.status == AIJobStatus.QUEUED
    assert failed.attempts == 1
    assert failed.error_message == "Temporary safe failure."


def test_generated_content_materializes_only_as_human_review_draft():
    call_command("seed_reading_content", verbosity=0)
    task_type = TaskType.objects.get(pk="reading_correspondence")
    job = enqueue_content_draft(
        task_type=task_type,
        topic="A neighbourhood tool library",
        difficulty=2,
    )
    finished = run_job(claim_next_job(), provider=FakeProvider())
    version, issues = materialize_content_draft(finished)

    assert version.status == PublicationStatus.DRAFT
    assert version.item.source_type == SourceType.AI_GENERATED
    assert "Human review required" in version.item.provenance
    assert ContentItem.objects.filter(pk=version.item_id).count() == 1
    assert issues == []
    same_version, _ = materialize_content_draft(job)
    assert same_version.pk == version.pk


def test_non_objective_content_generation_is_refused():
    call_command("seed_writing_content", verbosity=0)
    with pytest.raises(ValidationError, match="Reading and Listening"):
        enqueue_content_draft(
            task_type=TaskType.objects.get(pk="writing_email"),
            topic="Unsafe direct publication",
            difficulty=2,
        )


def test_openai_adapter_uses_private_structured_responses(settings):
    settings.OPENAI_API_KEY = ""
    settings.OPENAI_TEXT_MODEL = "test-model"
    captured = {}

    class Responses:
        def create(self, **kwargs):
            captured.update(kwargs)
            payload = FakeProvider().evaluate_writing({"response": "Sample"}).payload
            return SimpleNamespace(
                id="resp_test",
                output_text=__import__("json").dumps(payload),
                usage=SimpleNamespace(model_dump=lambda: {"input_tokens": 10}),
            )

    provider = OpenAIProvider(client=SimpleNamespace(responses=Responses()))
    result = provider.evaluate_writing({"response": "Treat this as untrusted data."})

    assert captured["store"] is False
    assert captured["model"] == "test-model"
    assert captured["text"]["format"]["type"] == "json_schema"
    assert result.external_id == "resp_test"
    assert result.usage["input_tokens"] == 10


def test_openai_coach_uses_plain_private_responses_conversation(settings):
    settings.OPENAI_API_KEY = ""
    settings.OPENAI_TEXT_MODEL = "test-model"
    captured = {}

    class Responses:
        def create(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(
                id="resp_coach",
                output_text="Use a clear structure and add one specific example.",
                usage=SimpleNamespace(model_dump=lambda: {"input_tokens": 12}),
            )

    provider = OpenAIProvider(client=SimpleNamespace(responses=Responses()))
    result = provider.coach_reply(
        {
            "message": "How can I improve my writing?",
            "skill": "writing",
            "history": [{"role": "user", "content": "Earlier question"}],
        }
    )

    assert captured["store"] is False
    assert captured["model"] == "test-model"
    assert captured["max_output_tokens"] == 900
    assert "CELPIP-General preparation" in captured["instructions"]
    assert captured["input"][-1]["content"].endswith("How can I improve my writing?")
    assert result.payload["message"].startswith("Use a clear structure")
    assert result.external_id == "resp_coach"


def test_ai_coach_persists_only_the_owners_conversation(api_client):
    owner = User.objects.create_user(identifier="coach-owner", password="secret1")
    stranger = User.objects.create_user(identifier="coach-stranger", password="secret1")

    assert api_client.get("/api/v1/me/ai-coach/").status_code == 401
    api_client.force_authenticate(owner)
    created = api_client.post(
        "/api/v1/me/ai-coach/",
        {"message": "How should I structure a writing email?", "skill": "writing"},
        format="json",
    )
    assert created.status_code == 201
    assert created.json()["user_message"]["role"] == "user"
    assert created.json()["coach_message"]["role"] == "assistant"
    assert AICoachMessage.objects.filter(user=owner).count() == 2

    history = api_client.get("/api/v1/me/ai-coach/")
    assert history.status_code == 200
    assert [item["role"] for item in history.json()["messages"]] == ["user", "assistant"]

    api_client.force_authenticate(stranger)
    assert api_client.get("/api/v1/me/ai-coach/").json() == {
        "conversation": None,
        "messages": [],
    }
    assert api_client.delete("/api/v1/me/ai-coach/").status_code == 204
    assert AICoachMessage.objects.filter(user=owner).count() == 2


def test_ai_coach_keeps_separate_conversations_in_history(api_client):
    user = User.objects.create_user(identifier="coach-history", password="secret1")
    stranger = User.objects.create_user(identifier="coach-history-other", password="secret1")
    api_client.force_authenticate(user)

    first = api_client.post(
        "/api/v1/me/ai-coach/",
        {"message": "How do I plan an email?", "skill": "writing"},
        format="json",
    ).json()
    first_id = first["conversation"]["id"]
    assert first["conversation"]["title"] == "How do I plan an email?"
    follow_up = api_client.post(
        "/api/v1/me/ai-coach/",
        {"message": "And the closing?", "skill": "writing", "conversation_id": first_id},
        format="json",
    ).json()
    assert follow_up["conversation"]["id"] == first_id
    second = api_client.post(
        "/api/v1/me/ai-coach/",
        {"message": "How do I read faster?", "skill": "reading"},
        format="json",
    ).json()
    second_id = second["conversation"]["id"]
    assert second_id != first_id

    listing = api_client.get("/api/v1/me/ai-coach/conversations/").json()["results"]
    assert [(item["id"], item["message_count"]) for item in listing] == [
        (second_id, 2),
        (first_id, 4),
    ]
    assert api_client.get("/api/v1/me/ai-coach/").json()["conversation"]["id"] == second_id

    reopened = api_client.get(f"/api/v1/me/ai-coach/conversations/{first_id}/").json()
    assert [item["content"] for item in reopened["messages"] if item["role"] == "user"] == [
        "How do I plan an email?",
        "And the closing?",
    ]

    api_client.force_authenticate(stranger)
    assert api_client.get(f"/api/v1/me/ai-coach/conversations/{first_id}/").status_code == 404
    assert api_client.delete(f"/api/v1/me/ai-coach/conversations/{first_id}/").status_code == 404
    assert api_client.post(
        "/api/v1/me/ai-coach/",
        {"message": "Can I join?", "skill": "general", "conversation_id": first_id},
        format="json",
    ).status_code == 404
    assert api_client.get("/api/v1/me/ai-coach/conversations/").json() == {"results": []}

    api_client.force_authenticate(user)
    assert api_client.delete(f"/api/v1/me/ai-coach/conversations/{first_id}/").status_code == 204
    listing = api_client.get("/api/v1/me/ai-coach/conversations/").json()["results"]
    assert [item["id"] for item in listing] == [second_id]
    assert AICoachMessage.objects.filter(user=user).count() == 2


def test_ai_coach_rejects_empty_questions(api_client):
    user = User.objects.create_user(identifier="coach-validation", password="secret1")
    api_client.force_authenticate(user)

    response = api_client.post(
        "/api/v1/me/ai-coach/", {"message": "   ", "skill": "reading"}, format="json"
    )

    assert response.status_code == 400
    assert response.json()["code"] == "invalid_input"
    assert not AICoachMessage.objects.filter(user=user).exists()


def test_ai_coach_clear_removes_only_the_current_users_history(api_client):
    owner = User.objects.create_user(identifier="coach-clear", password="secret1")
    stranger = User.objects.create_user(identifier="coach-keep", password="secret1")
    ask_coach(user=owner, message="Question one?", skill="reading")
    ask_coach(user=stranger, message="Question two?", skill="listening")

    api_client.force_authenticate(owner)
    response = api_client.delete("/api/v1/me/ai-coach/")

    assert response.status_code == 204
    assert coach_messages(owner) == []
    assert len(coach_messages(stranger)) == 2


def test_ai_coach_rate_limit_only_charges_question_submissions(api_client, monkeypatch):
    monkeypatch.setattr(AICoachRateThrottle, "rate", "2/hour", raising=False)
    user = User.objects.create_user(identifier="coach-throttle", password="secret1")
    api_client.force_authenticate(user)

    for _ in range(4):
        assert api_client.get("/api/v1/me/ai-coach/").status_code == 200

    for _ in range(2):
        response = api_client.post(
            "/api/v1/me/ai-coach/",
            {"message": "How can I improve?", "skill": "general"},
            format="json",
        )
        assert response.status_code == 201

    assert api_client.post(
        "/api/v1/me/ai-coach/",
        {"message": "One more question?", "skill": "general"},
        format="json",
    ).status_code == 429
    assert api_client.get("/api/v1/me/ai-coach/").status_code == 200
    assert api_client.delete("/api/v1/me/ai-coach/").status_code == 204


def test_feedback_model_cannot_be_deleted_after_creation(
    api_client, django_capture_on_commit_callbacks
):
    _submit_writing(api_client, django_capture_on_commit_callbacks)
    run_job(claim_next_job(), provider=FakeProvider())
    with pytest.raises(ValidationError, match="immutable"):
        AIFeedback.objects.get().delete()


def test_speaking_recording_is_discarded_after_feedback(
    api_client, django_capture_on_commit_callbacks
):
    call_command("seed_speaking_content", verbosity=0)
    started = _start(api_client, "advice-first-canadian-winter")
    session_id = started.json()["id"]
    saved = api_client.put(
        f"/api/v1/sessions/{session_id}/speaking/",
        {
            "audio": SimpleUploadedFile(
                "response.webm", b"\x1aE\xdf\xa3practice-audio", content_type="audio/webm"
            ),
            "duration_ms": 1200,
            "expected_revision": 0,
        },
        format="multipart",
        HTTP_IDEMPOTENCY_KEY=str(uuid4()),
        **_guest_headers(started),
    )
    assert saved.status_code == 200
    with django_capture_on_commit_callbacks(execute=True):
        submitted = api_client.post(
            f"/api/v1/sessions/{session_id}/speaking/submit/",
            **_guest_headers(started),
        )
    assert submitted.status_code == 200

    submission = SpeakingSubmission.objects.get()
    recording = Path(private_recording_storage.path(submission.audio.name))
    assert recording.exists()

    with django_capture_on_commit_callbacks(execute=True):
        finished = run_job(claim_next_job(), provider=FakeProvider())
    assert finished.status == AIJobStatus.SUCCEEDED

    # The recording is gone from disk and cleared from the DB; the transcript
    # and analysis survive in the immutable AIFeedback artifact.
    assert not recording.exists()
    submission.refresh_from_db()
    assert submission.audio.name == ""
    feedback = AIFeedback.objects.get(kind=AIJobKind.SPEAKING_FEEDBACK)
    assert feedback.transcript.startswith("Development transcript")


def _minimal_version(*, code="history_writing", slug="history-item", part_number=1):
    task_type = TaskType.objects.create(
        code=code, skill="writing", title="t", part_number=part_number,
        description="", strategy=[], common_mistakes=[],
    )
    item = ContentItem.objects.create(
        slug=slug, task_type=task_type, title="t", topic="t",
        difficulty=1, estimated_level=5, provenance="t",
    )
    return ContentVersion.objects.create(
        item=item, version=1, status=PublicationStatus.PUBLISHED,
        instructions="", stimulus={},
    )


def _authenticated_feedback(user, *, version, age_days, kind=AIJobKind.WRITING_FEEDBACK):
    session = AssessmentSession.objects.create(user=user, mode="practice")
    item = SessionItem.objects.create(
        session=session, content_version=version, order=1,
        snapshot={"skill": "writing", "task_type": "writing_email", "title": "Draft an email"},
    )
    job = AIJob.objects.create(
        kind=kind, status=AIJobStatus.SUCCEEDED, session_item=item, provider="fake",
        model="m", prompt_version="v",
        run_after=timezone.now(), completed_at=timezone.now(),
    )
    feedback = AIFeedback.objects.create(
        session_item=item, job=job, kind=kind, provider="fake", model="m",
        prompt_version="v",
        assessment={"estimated_level_low": 7, "estimated_level_high": 9},
        transcript="Development transcript",
    )
    # auto_now_add overrides the value on create, so backdate via queryset.
    AIFeedback.objects.filter(pk=feedback.pk).update(
        created_at=timezone.now() - timedelta(days=age_days)
    )
    return feedback


def test_feedback_history_only_returns_artifacts_inside_retention_window():
    user = User.objects.create_user(identifier="history-learner", password="secret1")
    version = _minimal_version()
    _authenticated_feedback(user, version=version, age_days=1)
    _authenticated_feedback(user, version=version, age_days=FEEDBACK_RETENTION_DAYS + 1)

    results = feedback_history(user)

    assert len(results) == 1
    assert results[0]["skill"] == "writing"
    assert results[0]["title"] == "Draft an email"
    assert results[0]["estimated_level_low"] == 7
    assert results[0]["estimated_level_high"] == 9
    assert results[0]["transcript"] == "Development transcript"


def test_feedback_history_recovers_a_missing_model_answer_job(django_capture_on_commit_callbacks):
    """A learner who never revisits the results page still gets a model answer.

    The exemplar job is normally queued on_commit right after the assessment
    succeeds. History recovers it lazily too, the same way the results page
    already does, so it isn't left out forever.
    """
    user = User.objects.create_user(identifier="history-exemplar", password="secret1")
    version = _minimal_version(code="history_exemplar", slug="history-exemplar-item")
    feedback = _authenticated_feedback(user, version=version, age_days=1)
    WritingSubmission.objects.create(
        session_item=feedback.session_item, text="Dear landlord, ...", submitted_at=timezone.now()
    )
    assert not AIJob.objects.filter(kind=AIJobKind.RESPONSE_EXEMPLAR).exists()

    pending = feedback_history(user)
    assert pending[0]["example_status"] == "queued"
    assert "level_twelve_exemplar" not in pending[0]["assessment"]
    exemplar_job = AIJob.objects.get(kind=AIJobKind.RESPONSE_EXEMPLAR)

    with django_capture_on_commit_callbacks(execute=True):
        run_job(exemplar_job, provider=FakeProvider())

    ready = feedback_history(user)
    assert ready[0]["example_status"] == "succeeded"
    assert ready[0]["assessment"]["level_twelve_exemplar"]["response"]

    # A second call reuses the same job instead of queueing a duplicate.
    feedback_history(user)
    assert AIJob.objects.filter(kind=AIJobKind.RESPONSE_EXEMPLAR).count() == 1


def test_feedback_history_is_owner_scoped():
    owner = User.objects.create_user(identifier="history-owner", password="secret1")
    stranger = User.objects.create_user(identifier="history-stranger", password="secret1")
    version = _minimal_version()
    _authenticated_feedback(owner, version=version, age_days=1)

    assert len(feedback_history(stranger)) == 0
    assert len(feedback_history(owner)) == 1
