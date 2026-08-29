"""Privacy-safe account data export.

Assembles everything the authenticated learner has created or produced on the
platform — profile, attempts, progress, mistakes, study plans, mock summaries,
and authored response text/metadata — into a single JSON document.

The export is intentionally *exclusive*: it never includes password/recovery
hashes, JWT or guest tokens, idempotency keys, content answer keys (correct
choices, evidence, or explanations for the frozen question bank), other users'
data, or the binary contents of private speaking recordings.
"""
from __future__ import annotations

from django.utils import timezone

from apps.ai_services.models import AIFeedback
from apps.assessments.models import (
    AssessmentSession,
    ObjectiveResult,
    Response,
    SpeakingRetry,
    SpeakingSubmission,
    WritingSubmission,
)
from apps.learning.models import MistakeRecord, StudyPlan
from apps.learning.services import plan_payload, progress_payload
from apps.mocks.models import MockAttempt
from apps.mocks.services import MockError, attempt_payload, results_payload

from .models import User
from .serializers import LearnerProfileSerializer, UserSerializer

EXPORT_FORMAT_VERSION = "1.0"


def _content_summary(snapshot: dict) -> dict:
    """Identify the attempted content without exposing its answer key."""
    return {
        "slug": snapshot.get("slug"),
        "title": snapshot.get("title"),
        "topic": snapshot.get("topic"),
        "task_type": snapshot.get("task_type"),
        "skill": snapshot.get("skill"),
    }


def _sanitized_outcome(outcome: dict) -> dict:
    """Keep only the learner's own result; strip correct-choice/evidence keys."""
    return {
        "question_id": outcome.get("question_id"),
        "selected_choice_id": outcome.get("selected_choice_id"),
        "is_correct": outcome.get("is_correct"),
    }


def _objective_result_payload(result: ObjectiveResult | None) -> dict | None:
    if result is None:
        return None
    return {
        "raw_correct": result.raw_correct,
        "raw_possible": result.raw_possible,
        "scored_at": result.scored_at,
        "outcomes": [
            _sanitized_outcome(outcome) for outcome in (result.outcomes or [])
        ],
    }


def _writing_payload(submission: WritingSubmission | None) -> dict | None:
    if submission is None:
        return None
    return {
        "text": submission.text,
        "word_count": submission.word_count,
        "revision": submission.revision,
        "saved_at": submission.saved_at,
        "submitted_at": submission.submitted_at,
    }


def _speaking_payload(submission: SpeakingSubmission | None) -> dict | None:
    """Speaking *metadata* only — the private audio binary is never exported."""
    if submission is None:
        return None
    return {
        "mime_type": submission.mime_type,
        "container": submission.container,
        "byte_size": submission.byte_size,
        "duration_ms": submission.duration_ms,
        "revision": submission.revision,
        "saved_at": submission.saved_at,
        "submitted_at": submission.submitted_at,
    }


def _feedback_payload(feedback: AIFeedback | None) -> dict | None:
    if feedback is None:
        return None
    return {
        "kind": feedback.kind,
        "transcript": feedback.transcript,
        "assessment": feedback.assessment,
        "provider": feedback.provider,
        "model": feedback.model,
        "prompt_version": feedback.prompt_version,
        "created_at": feedback.created_at,
    }


def _attempt_payload(session: AssessmentSession) -> dict:
    """Attempt number and retry linkage IDs, never tokens or audio paths."""
    payload: dict = {"attempt_number": session.attempt_number}
    try:
        payload["retry_id"] = str(session.speaking_retry.retry_id)
    except SpeakingRetry.DoesNotExist:
        pass
    try:
        payload["source_id"] = str(session.speaking_retry_of.source_id)
    except SpeakingRetry.DoesNotExist:
        pass
    return payload


def _sessions(user: User) -> list[dict]:
    sessions = (
        AssessmentSession.objects.filter(user=user)
        .select_related("objective_result")
        .prefetch_related("items")
    )
    exported: list[dict] = []
    for session in sessions:
        item = session.items.first()
        snapshot = item.snapshot if item else {}
        responses = list(
            Response.objects.filter(session_item=item).values(
                "question_id", "selected_choice_id", "revision", "saved_at"
            )
        ) if item else []

        writing = None
        speaking = None
        feedback = None
        if item:
            writing = WritingSubmission.objects.filter(session_item=item).first()
            speaking = SpeakingSubmission.objects.filter(session_item=item).first()
            try:
                feedback = item.ai_feedback
            except AIFeedback.DoesNotExist:
                feedback = None

        exported.append(
            {
                "id": str(session.id),
                "mode": session.mode,
                "state": session.state,
                "started_at": session.started_at,
                "deadline_at": session.deadline_at,
                "submitted_at": session.submitted_at,
                "content": _content_summary(snapshot),
                "responses": responses,
                "writing_submission": _writing_payload(writing),
                "speaking_submission": _speaking_payload(speaking),
                "objective_result": _objective_result_payload(
                    getattr(session, "objective_result", None)
                ),
                "ai_feedback": _feedback_payload(feedback),
                "attempt": _attempt_payload(session),
            }
        )
    return exported


def _mistakes(user: User) -> list[dict]:
    # Answer-revealing fields (correct_snapshot, explanation_snapshot) are
    # intentionally excluded: the export records *what the learner chose* and
    # its status, never the frozen question bank's correct answer or rationale.
    return list(
        MistakeRecord.objects.filter(user=user)
        .select_related("task_type")
        .values(
            "id",
            "skill",
            "task_type_id",
            "stem_snapshot",
            "selected_snapshot",
            "occurrences",
            "state",
            "first_seen_at",
            "last_seen_at",
            "resolved_at",
        )
    )


def _study_plans(user: User) -> list[dict]:
    return [
        plan_payload(plan)
        for plan in StudyPlan.objects.filter(user=user).prefetch_related(
            "tasks__task_type"
        )
    ]


def _mock_attempts(user: User) -> list[dict]:
    attempts = MockAttempt.objects.filter(user=user).prefetch_related("tasks")
    exported: list[dict] = []
    for attempt in attempts:
        payload = attempt_payload(attempt, include_tasks=True)
        # attempt_payload embeds server_now, which is not learner data; drop it.
        payload.pop("server_now", None)
        try:
            payload["results"] = results_payload(attempt)
        except MockError:
            # Results are embargoed until a full mock completes.
            payload["results"] = None
        exported.append(payload)
    return exported


def build_export(user: User) -> dict:
    """Return the learner's complete, privacy-safe export document."""
    return {
        "format_version": EXPORT_FORMAT_VERSION,
        "exported_at": timezone.now(),
        "account": UserSerializer(user).data,
        "profile": LearnerProfileSerializer(user.profile).data,
        "sessions": _sessions(user),
        "progress": progress_payload(user),
        "mistakes": _mistakes(user),
        "study_plans": _study_plans(user),
        "mock_attempts": _mock_attempts(user),
    }
