"""Provider contracts, audited jobs, feedback privacy, and draft review gates."""

from types import SimpleNamespace
from uuid import uuid4

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command

from apps.ai_services.contracts import ProviderError, ProviderResult
from apps.ai_services.models import AIFeedback, AIJob, AIJobKind, AIJobStatus
from apps.ai_services.providers import FakeProvider, OpenAIProvider
from apps.ai_services.services import (
    claim_next_job,
    enqueue_content_draft,
    materialize_content_draft,
    run_job,
)
from apps.assessments.models import SpeakingSubmission
from apps.assessments.storage import private_recording_storage
from apps.content.models import ContentItem, PublicationStatus, SourceType, TaskType

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


def test_feedback_model_cannot_be_deleted_after_creation(
    api_client, django_capture_on_commit_callbacks
):
    _submit_writing(api_client, django_capture_on_commit_callbacks)
    run_job(claim_next_job(), provider=FakeProvider())
    with pytest.raises(ValidationError, match="immutable"):
        AIFeedback.objects.get().delete()
