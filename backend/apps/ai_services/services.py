"""Queue orchestration, output validation, and draft materialization."""

from __future__ import annotations

import logging
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.assessments.models import SpeakingSubmission, WritingSubmission
from apps.content.models import (
    Choice,
    ContentItem,
    ContentVersion,
    PublicationStatus,
    Question,
    SourceType,
    TaskType,
)
from apps.content.services import validate_content_version

from .contracts import ProviderError
from .models import AIFeedback, AIJob, AIJobKind, AIJobStatus
from .prompts import CONTENT_PROMPT_VERSION, FEEDBACK_PROMPT_VERSION
from .providers import get_provider
from .schemas import validate_content_draft, validate_feedback

logger = logging.getLogger(__name__)


def _model_for(kind: str) -> str:
    if kind == AIJobKind.SPEAKING_FEEDBACK:
        return f"{settings.OPENAI_TRANSCRIBE_MODEL}+{settings.OPENAI_TEXT_MODEL}"
    return settings.OPENAI_TEXT_MODEL


def enqueue_feedback(session_item) -> AIJob:
    """Create at most one feedback job for the frozen submitted item."""
    skill = session_item.snapshot.get("skill")
    if skill == "writing":
        kind = AIJobKind.WRITING_FEEDBACK
        submission = WritingSubmission.objects.get(session_item=session_item)
        if not submission.is_submitted:
            raise ValidationError("Writing must be submitted before AI feedback is queued.")
        response_data = {"response": submission.text}
    elif skill == "speaking":
        kind = AIJobKind.SPEAKING_FEEDBACK
        submission = SpeakingSubmission.objects.get(session_item=session_item)
        if not submission.is_submitted:
            raise ValidationError("Speaking must be submitted before AI feedback is queued.")
        response_data = {
            "recording_duration_ms": submission.duration_ms,
            "recording_revision": submission.revision,
        }
    else:
        raise ValidationError("AI feedback is available for Writing and Speaking only.")

    existing = AIJob.objects.filter(session_item=session_item, kind=kind).first()
    if existing:
        return existing
    return AIJob.objects.create(
        kind=kind,
        user=session_item.session.user,
        session_item=session_item,
        provider=settings.AI_PROVIDER,
        model=_model_for(kind),
        prompt_version=FEEDBACK_PROMPT_VERSION,
        input_snapshot={
            "skill": skill,
            "task_type": session_item.snapshot.get("task_type"),
            "instructions": session_item.snapshot.get("instructions"),
            "stimulus": session_item.snapshot.get("stimulus"),
            **response_data,
        },
        max_attempts=settings.AI_MAX_ATTEMPTS,
        run_after=timezone.now(),
    )


def enqueue_content_draft(*, task_type: TaskType, topic: str, difficulty: int, user=None) -> AIJob:
    if task_type.skill not in {"reading", "listening"}:
        raise ValidationError("Objective AI drafts currently support Reading and Listening.")
    if not 1 <= difficulty <= 3:
        raise ValidationError("Difficulty must be between 1 and 3.")
    return AIJob.objects.create(
        kind=AIJobKind.CONTENT_DRAFT,
        user=user,
        provider=settings.AI_PROVIDER,
        model=settings.OPENAI_TEXT_MODEL,
        prompt_version=CONTENT_PROMPT_VERSION,
        input_snapshot={
            "task_type": task_type.pk,
            "task_title": task_type.title,
            "skill": task_type.skill,
            "topic": topic.strip(),
            "difficulty": difficulty,
            "editorial_requirements": {
                "original": True,
                "canadian_context": True,
                "human_review_required": True,
            },
        },
        max_attempts=settings.AI_MAX_ATTEMPTS,
        run_after=timezone.now(),
    )


@transaction.atomic
def claim_next_job() -> AIJob | None:
    now = timezone.now()
    job = (
        AIJob.objects.select_for_update()
        .filter(status=AIJobStatus.QUEUED, run_after__lte=now)
        .order_by("created_at")
        .first()
    )
    if job is None:
        return None
    job.status = AIJobStatus.RUNNING
    job.locked_at = now
    job.attempts += 1
    job.error_code = ""
    job.error_message = ""
    job.save(
        update_fields=[
            "status",
            "locked_at",
            "attempts",
            "error_code",
            "error_message",
            "updated_at",
        ]
    )
    return job


def run_job(job: AIJob, *, provider=None) -> AIJob:
    provider = provider or get_provider()
    try:
        if job.kind == AIJobKind.WRITING_FEEDBACK:
            result = provider.evaluate_writing(job.input_snapshot)
            payload = validate_feedback(result.payload)
            transcript = ""
        elif job.kind == AIJobKind.SPEAKING_FEEDBACK:
            submission = SpeakingSubmission.objects.get(session_item=job.session_item)
            result = provider.evaluate_speaking(Path(submission.audio.path), job.input_snapshot)
            transcript = str(result.payload.pop("transcript", ""))
            payload = validate_feedback(result.payload)
        elif job.kind == AIJobKind.CONTENT_DRAFT:
            result = provider.generate_content(job.input_snapshot)
            payload = validate_content_draft(result.payload)
            transcript = ""
        else:
            raise ProviderError(
                "unsupported_job", "This AI job kind is not implemented.", retryable=False
            )
    except ProviderError as exc:
        return _record_failure(job, exc)
    except Exception:
        logger.exception("Unexpected failure while processing AI job %s", job.pk)
        return _record_failure(
            job,
            ProviderError("internal_error", "The AI job failed safely."),
        )

    with transaction.atomic():
        locked = AIJob.objects.select_for_update().get(pk=job.pk)
        locked.output = payload
        locked.external_id = result.external_id
        locked.usage = result.usage
        locked.status = AIJobStatus.SUCCEEDED
        locked.completed_at = timezone.now()
        locked.locked_at = None
        locked.save(
            update_fields=[
                "output",
                "external_id",
                "usage",
                "status",
                "completed_at",
                "locked_at",
                "updated_at",
            ]
        )
        if locked.kind in {AIJobKind.WRITING_FEEDBACK, AIJobKind.SPEAKING_FEEDBACK}:
            AIFeedback.objects.get_or_create(
                session_item=locked.session_item,
                defaults={
                    "job": locked,
                    "kind": locked.kind,
                    "provider": locked.provider,
                    "model": locked.model,
                    "prompt_version": locked.prompt_version,
                    "transcript": transcript,
                    "assessment": payload,
                },
            )
    return locked


def _record_failure(job: AIJob, exc: ProviderError) -> AIJob:
    with transaction.atomic():
        locked = AIJob.objects.select_for_update().get(pk=job.pk)
        should_retry = exc.retryable and locked.attempts < locked.max_attempts
        locked.status = AIJobStatus.QUEUED if should_retry else AIJobStatus.FAILED
        locked.run_after = timezone.now() + timedelta(seconds=2**locked.attempts)
        locked.locked_at = None
        locked.error_code = exc.code
        locked.error_message = str(exc)[:500]
        if not should_retry:
            locked.completed_at = timezone.now()
        locked.save(
            update_fields=[
                "status",
                "run_after",
                "locked_at",
                "error_code",
                "error_message",
                "completed_at",
                "updated_at",
            ]
        )
    return locked


@transaction.atomic
def materialize_content_draft(job: AIJob) -> tuple[ContentVersion, list]:
    """Turn successful output into a reviewable draft; never publish it."""
    locked = AIJob.objects.select_for_update().get(pk=job.pk)
    if locked.kind != AIJobKind.CONTENT_DRAFT or locked.status != AIJobStatus.SUCCEEDED:
        raise ValidationError("Only a successful content-draft job can be materialized.")
    if locked.content_version_id:
        return locked.content_version, validate_content_version(locked.content_version)

    data = validate_content_draft(dict(locked.output))
    task_type = TaskType.objects.get(pk=locked.input_snapshot["task_type"], is_active=True)
    slug = data["slug"][:120]
    if ContentItem.objects.filter(slug=slug).exists():
        slug = f"{slug[:110]}-{str(locked.pk)[:8]}"
    item = ContentItem.objects.create(
        slug=slug,
        task_type=task_type,
        title=data["title"][:180],
        topic=data["topic"][:120],
        difficulty=data["difficulty"],
        estimated_level=data["estimated_level"],
        source_type=SourceType.AI_GENERATED,
        author=locked.user,
        provenance=(
            f"AI editorial draft from job {locked.pk}; provider={locked.provider}; "
            f"model={locked.model}; prompt={locked.prompt_version}. Human review required."
        ),
    )
    version = ContentVersion.objects.create(
        item=item,
        version=1,
        status=PublicationStatus.DRAFT,
        instructions=data["instructions"],
        stimulus=data["stimulus"],
        learning_notes=data["learning_notes"],
    )
    for question_order, question_data in enumerate(data["questions"], 1):
        question = Question.objects.create(
            content_version=version,
            order=question_order,
            stem=question_data["stem"],
            skill_focus=question_data["skill_focus"],
            evidence=question_data["evidence"],
            explanation=question_data["explanation"],
        )
        for choice_order, choice_data in enumerate(question_data["choices"], 1):
            Choice.objects.create(
                question=question,
                order=choice_order,
                text=choice_data["text"],
                is_correct=choice_data["is_correct"],
                explanation=choice_data["explanation"],
            )
    locked.content_version = version
    locked.save(update_fields=["content_version", "updated_at"])
    return version, validate_content_version(version)


def feedback_payload(session_item) -> dict:
    try:
        feedback = session_item.ai_feedback
    except AIFeedback.DoesNotExist:
        job = session_item.ai_jobs.order_by("-created_at").first()
        if job is None:
            return {"status": "not_requested"}
        return {
            "status": job.status,
            "job_id": str(job.pk),
            "attempts": job.attempts,
            "error": job.error_message if job.status == AIJobStatus.FAILED else "",
        }
    return {
        "status": "succeeded",
        "job_id": str(feedback.job_id),
        "kind": feedback.kind,
        "transcript": feedback.transcript,
        "assessment": feedback.assessment,
        "audit": {
            "provider": feedback.provider,
            "model": feedback.model,
            "prompt_version": feedback.prompt_version,
            "created_at": feedback.created_at,
        },
    }
