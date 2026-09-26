"""Queue orchestration, output validation, and draft materialization."""

from __future__ import annotations

import logging
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import transaction
from django.db.models import Count
from django.utils import timezone

from apps.assessments.models import SpeakingSubmission, WritingSubmission
from apps.assessments.storage import private_recording_storage
from apps.content.answer_patterns import grading_pattern
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
from .models import AICoachConversation, AICoachMessage, AIFeedback, AIJob, AIJobKind, AIJobStatus
from .prompts import (
    COACH_PROMPT_VERSION,
    CONTENT_PROMPT_VERSION,
    EXEMPLAR_PROMPT_VERSION,
    FEEDBACK_PROMPT_VERSION,
)
from .providers import get_provider
from .schemas import (
    validate_coach_reply,
    validate_content_draft,
    validate_exemplar,
    validate_feedback,
)

logger = logging.getLogger(__name__)

# How long authenticated learners can revisit an AI feedback artifact (the
# transcript + analysis + score). After this, the retention command purges it.
# The audio recording is dropped much earlier — immediately once feedback lands.
FEEDBACK_RETENTION_DAYS = 180
COACH_HISTORY_LIMIT = 200
COACH_CONTEXT_MESSAGES = 12
COACH_MAX_MESSAGE_LENGTH = 8000
COACH_TITLE_LENGTH = 120
COACH_SKILLS = {"general", "listening", "reading", "writing", "speaking"}
# An example answer is shown only after the same grader places it at this
# level or above; otherwise one more draft is written from the grader's notes.
EXEMPLAR_TARGET_LEVEL = 11
EXEMPLAR_MAX_DRAFTS = 2
# Learners read a spoken example aloud, so it must fit the response time at a
# comfortable pace (about 120 words per minute) or the recording cuts it off.
SPOKEN_WORDS_PER_SECOND = 2.0


def discard_speaking_audio(submission) -> None:
    """Remove the private recording for an analyzed Speaking attempt.

    Feedback needs the audio once, at evaluation time. After that the recording
    is personal data the learner no longer needs (the transcript is kept in
    AIFeedback), so it is deleted the moment analysis succeeds.
    """
    if not submission.audio.name:
        return
    try:
        private_recording_storage.delete(submission.audio.name)
    except FileNotFoundError:
        logger.warning("Speaking audio already missing: %s", submission.audio.name)
    SpeakingSubmission.objects.filter(pk=submission.pk).update(audio="")


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
            "answer_pattern": grading_pattern(session_item.snapshot.get("task_type")),
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


def enqueue_response_exemplar(session_item) -> AIJob:
    """Queue one independently retryable example answer after scoring succeeds."""
    existing = AIJob.objects.filter(
        session_item=session_item,
        kind=AIJobKind.RESPONSE_EXEMPLAR,
        prompt_version=EXEMPLAR_PROMPT_VERSION,
    ).first()
    if existing:
        return existing
    skill = session_item.snapshot.get("skill")
    learner_response = ""
    if skill == "writing":
        learner_response = WritingSubmission.objects.get(session_item=session_item).text
    elif skill == "speaking":
        feedback = AIFeedback.objects.filter(session_item=session_item).first()
        if feedback:
            learner_response = feedback.transcript
    feedback = AIFeedback.objects.filter(session_item=session_item).first()
    feedback_context = feedback.assessment if feedback else {}
    stimulus = session_item.snapshot.get("stimulus") or {}
    word_budget = {}
    if skill == "speaking" and stimulus.get("response_seconds"):
        word_budget["max_words"] = int(stimulus["response_seconds"] * SPOKEN_WORDS_PER_SECOND)
    return AIJob.objects.create(
        kind=AIJobKind.RESPONSE_EXEMPLAR,
        user=session_item.session.user,
        session_item=session_item,
        provider=settings.AI_PROVIDER,
        model=settings.OPENAI_TEXT_MODEL,
        prompt_version=EXEMPLAR_PROMPT_VERSION,
        input_snapshot={
            "skill": skill,
            "task_type": session_item.snapshot.get("task_type"),
            "instructions": session_item.snapshot.get("instructions"),
            "stimulus": session_item.snapshot.get("stimulus"),
            "learner_response": learner_response,
            "feedback": feedback_context,
            "answer_pattern": grading_pattern(session_item.snapshot.get("task_type")),
            **word_budget,
        },
        max_attempts=settings.AI_MAX_ATTEMPTS,
        run_after=timezone.now(),
    )


@transaction.atomic
def claim_next_job() -> AIJob | None:
    """Lock and claim the oldest due job.

    ``skip_locked`` lets several worker processes run concurrently: a worker
    that finds the oldest row already locked by another worker moves on to
    the next one instead of blocking behind it. PostgreSQL (production)
    honours this; SQLite (dev/tests) ignores it silently and behaves as
    before, since it has no row locking at all.
    """
    now = timezone.now()
    job = (
        AIJob.objects.select_for_update(skip_locked=True)
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
        elif job.kind == AIJobKind.RESPONSE_EXEMPLAR:
            result, payload = _generate_checked_exemplar(provider, job.input_snapshot)
            transcript = ""
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
            if locked.user_id:
                from apps.learning.services import regenerate_plan

                transaction.on_commit(lambda: regenerate_plan(locked.user), robust=True)
            if locked.kind == AIJobKind.SPEAKING_FEEDBACK:
                transaction.on_commit(
                    lambda: discard_speaking_audio(submission), robust=True
                )
            transaction.on_commit(
                lambda: enqueue_response_exemplar(locked.session_item), robust=True
            )
    return locked


def _generate_checked_exemplar(provider, snapshot: dict):
    """Write an example answer and grade it with the learner's own grader.

    The level the grader gives is stored on the example, so the page never
    promises a level the grader itself would not award. The best-scoring
    draft is kept if none reaches the target.
    """
    grading_request = {
        key: snapshot.get(key)
        for key in ("skill", "task_type", "instructions", "stimulus", "answer_pattern")
    }
    answer_key = "transcript" if snapshot.get("skill") == "speaking" else "response"
    max_words = snapshot.get("max_words")
    request = snapshot
    best = None
    for _ in range(EXEMPLAR_MAX_DRAFTS):
        result = provider.generate_exemplar(request)
        exemplar = validate_exemplar(result.payload)
        check = validate_feedback(
            provider.grade_text(grading_request | {answer_key: exemplar["response"]}).payload
        )
        word_count = len(exemplar["response"].split())
        too_long = bool(max_words) and word_count > max_words
        exemplar["verified_level_low"] = check["estimated_level_low"]
        exemplar["verified_level_high"] = check["estimated_level_high"]
        rank = (not too_long, check["estimated_level_low"], check["estimated_level_high"])
        if best is None or rank > best[0]:
            best = (rank, result, exemplar)
        if not too_long and check["estimated_level_low"] >= EXEMPLAR_TARGET_LEVEL:
            break
        review = {
            "estimated_level_low": check["estimated_level_low"],
            "estimated_level_high": check["estimated_level_high"],
            "priorities": check["priorities"],
        }
        if too_long:
            review["priorities"] = [
                f"Cut the response from {word_count} to at most {max_words} words.",
                *review["priorities"],
            ]
        request = snapshot | {
            "previous_draft": exemplar["response"],
            "previous_draft_review": review,
        }
    _, result, exemplar = best
    return result, exemplar


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
            # Recover jobs whose transaction callback was interrupted by a
            # worker/web restart after the speaking or writing submission was
            # committed. Without this, the UI can poll "not_requested"
            # forever even though the attempt is already submitted.
            submission_relation = (
                "speaking_submission"
                if session_item.snapshot.get("skill") == "speaking"
                else "writing_submission"
            )
            submission = getattr(session_item, submission_relation, None)
            if session_item.session.state == "submitted" and submission and submission.is_submitted:
                try:
                    job = enqueue_feedback(session_item)
                except ValidationError:
                    job = None
            if job is not None:
                return {
                    "status": job.status,
                    "job_id": str(job.pk),
                    "attempts": job.attempts,
                    "error": "",
                }
            return {"status": "not_requested"}
        return {
            "status": job.status,
            "job_id": str(job.pk),
            "attempts": job.attempts,
            "error": job.error_message if job.status == AIJobStatus.FAILED else "",
        }
    exemplar_job = (
        session_item.ai_jobs.filter(kind=AIJobKind.RESPONSE_EXEMPLAR)
        .order_by("-created_at")
        .first()
    )
    # Feedback created during a deployment boundary may predate the on-commit
    # enqueue callback. Recover it lazily when the learner opens their result.
    if exemplar_job is None:
        exemplar_job = enqueue_response_exemplar(session_item)
    assessment = dict(feedback.assessment)
    example_status = exemplar_job.status
    if exemplar_job.status == AIJobStatus.SUCCEEDED:
        assessment["level_twelve_exemplar"] = exemplar_job.output
    return {
        "status": "succeeded",
        "job_id": str(feedback.job_id),
        "kind": feedback.kind,
        "transcript": feedback.transcript,
        "assessment": assessment,
        "example_status": example_status,
        "audit": {
            "provider": feedback.provider,
            "model": feedback.model,
            "prompt_version": feedback.prompt_version,
            "created_at": feedback.created_at,
        },
    }


def feedback_history(user) -> list[dict]:
    """Feedback artifacts a learner can still revisit, newest first.

    Only artifacts inside the retention window are returned, so once the
    retention command purges an artifact it also disappears from history. The
    audio is never returned (it is discarded on analysis); the transcript stays
    for Speaking so the learner can review what was said.
    """
    cutoff = timezone.now() - timedelta(days=FEEDBACK_RETENTION_DAYS)
    artifacts = (
        AIFeedback.objects.filter(
            session_item__session__user=user, created_at__gte=cutoff
        )
        .select_related("session_item")
        .order_by("-created_at")
    )
    results = []
    for artifact in artifacts:
        snapshot = artifact.session_item.snapshot
        assessment = dict(artifact.assessment)
        exemplar_job = (
            artifact.session_item.ai_jobs.filter(kind=AIJobKind.RESPONSE_EXEMPLAR)
            .order_by("-created_at")
            .first()
        )
        if exemplar_job is None:
            # The results page enqueues the model answer lazily when the learner
            # opens it; a learner who goes straight to the dashboard instead
            # never triggers that, so this history view recovers it the same
            # way rather than silently leaving the answer out forever.
            try:
                exemplar_job = enqueue_response_exemplar(artifact.session_item)
            except ObjectDoesNotExist:
                exemplar_job = None
        example_status = exemplar_job.status if exemplar_job else None
        if exemplar_job is not None and exemplar_job.status == AIJobStatus.SUCCEEDED:
            assessment["level_twelve_exemplar"] = exemplar_job.output
        results.append(
            {
                "created_at": artifact.created_at,
                "kind": artifact.kind,
                "skill": snapshot.get("skill"),
                "task_type": snapshot.get("task_type"),
                "title": snapshot.get("title", snapshot.get("task_type", "")),
                "estimated_level_low": assessment.get("estimated_level_low"),
                "estimated_level_high": assessment.get("estimated_level_high"),
                "transcript": artifact.transcript,
                "assessment": assessment,
                "example_status": example_status,
            }
        )
    return results


def latest_coach_conversation(user) -> AICoachConversation | None:
    """Return the chat the learner touched most recently, if any."""
    return AICoachConversation.objects.filter(user=user).first()


def coach_messages(user, conversation: AICoachConversation | None = None) -> list[AICoachMessage]:
    """Return a conversation's turns (the latest one by default) in natural order."""
    conversation = conversation or latest_coach_conversation(user)
    if conversation is None:
        return []
    recent = list(
        conversation.messages.order_by("-created_at", "-id")[:COACH_HISTORY_LIMIT]
    )
    recent.reverse()
    return recent


def coach_conversations(user):
    """List the learner's saved chats, newest activity first."""
    return AICoachConversation.objects.filter(user=user).annotate(
        message_count=Count("messages")
    )


def ask_coach(
    *,
    user,
    message: str,
    skill: str,
    conversation: AICoachConversation | None = None,
) -> tuple[AICoachMessage, AICoachMessage]:
    """Answer one learner turn and persist both sides of it.

    Without a ``conversation`` the question starts a new saved chat.
    """
    clean_message = (message or "").strip()
    clean_skill = (skill or "general").strip().lower()
    if not clean_message:
        raise ValidationError("Write a question before sending it.")
    if len(clean_message) > COACH_MAX_MESSAGE_LENGTH:
        raise ValidationError(
            f"Questions must be {COACH_MAX_MESSAGE_LENGTH} characters or fewer."
        )
    if clean_skill not in COACH_SKILLS:
        raise ValidationError("Choose a valid practice skill.")
    if conversation is not None and conversation.user_id != user.pk:
        raise ValidationError("Choose one of your own conversations.")

    recent = []
    if conversation is not None:
        recent = list(
            conversation.messages.order_by("-created_at", "-id")[:COACH_CONTEXT_MESSAGES]
        )
        recent.reverse()
    result = get_provider().coach_reply(
        {
            "message": clean_message,
            "skill": clean_skill,
            "history": [
                {"role": item.role, "content": item.content}
                for item in recent
            ],
        }
    )
    reply = validate_coach_reply(result.payload)

    with transaction.atomic():
        if conversation is None:
            conversation = AICoachConversation.objects.create(
                user=user,
                title=" ".join(clean_message.split())[:COACH_TITLE_LENGTH],
                skill=clean_skill,
            )
        else:
            conversation.skill = clean_skill
            conversation.save(update_fields=["skill", "updated_at"])
        learner_message = AICoachMessage.objects.create(
            user=user,
            conversation=conversation,
            role=AICoachMessage.Role.USER,
            content=clean_message,
            skill=clean_skill,
        )
        coach_message = AICoachMessage.objects.create(
            user=user,
            conversation=conversation,
            role=AICoachMessage.Role.ASSISTANT,
            content=reply,
            skill=clean_skill,
            provider=settings.AI_PROVIDER,
            model=settings.OPENAI_TEXT_MODEL,
            prompt_version=COACH_PROMPT_VERSION,
            external_id=result.external_id,
            usage=result.usage,
        )
    return learner_message, coach_message


def clear_coach_messages(user) -> int:
    """Delete every saved AI Coach conversation for the learner on request."""
    deleted, _ = AICoachConversation.objects.filter(user=user).delete()
    return deleted
