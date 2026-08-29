"""Transactional assessment creation, autosave, and scoring."""
from __future__ import annotations

import hashlib
import json
import secrets
from dataclasses import dataclass
from datetime import timedelta
from uuid import UUID

from django.db import transaction
from django.utils import timezone

from apps.content.models import Choice, ContentVersion, PublicationStatus, Question

from .models import (
    AssessmentSession,
    ObjectiveResult,
    Response,
    SessionItem,
    SessionMode,
    SessionState,
)


class AssessmentError(Exception):
    code = "assessment_error"


class SessionAccessDenied(AssessmentError):
    code = "session_access_denied"


class GuestAccessExpired(SessionAccessDenied):
    code = "guest_access_expired"


class SessionNotActive(AssessmentError):
    code = "session_not_active"


class SessionDeadlinePassed(AssessmentError):
    code = "session_deadline_passed"


class StaleRevision(AssessmentError):
    code = "stale_revision"


class IdempotencyConflict(AssessmentError):
    code = "idempotency_conflict"


class InvalidAnswer(AssessmentError):
    code = "invalid_answer"


class ContentUnavailable(AssessmentError):
    code = "content_unavailable"


@dataclass(frozen=True)
class StartedSession:
    session: AssessmentSession
    guest_token: str | None


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _snapshot(version: ContentVersion) -> dict:
    return {
        "slug": version.item.slug,
        "title": version.item.title,
        "topic": version.item.topic,
        "difficulty": version.item.difficulty,
        "estimated_level": version.item.estimated_level,
        "task_type": version.item.task_type_id,
        "instructions": version.instructions,
        "stimulus": version.stimulus,
        "learning_notes": version.learning_notes,
        "questions": [
            {
                "id": question.id,
                "order": question.order,
                "stem": question.stem,
                "skill_focus": question.skill_focus,
                "evidence": question.evidence,
                "explanation": question.explanation,
                "choices": [
                    {
                        "id": choice.id,
                        "order": choice.order,
                        "text": choice.text,
                        "is_correct": choice.is_correct,
                        "explanation": choice.explanation,
                    }
                    for choice in question.choices.all()
                ],
            }
            for question in version.questions.all()
        ],
    }


@transaction.atomic
def start_session(*, user, content_slug: str, mode: str, time_limit_seconds: int) -> StartedSession:
    try:
        version = (
            ContentVersion.objects.select_related("item")
            .prefetch_related("questions__choices")
            .get(item__slug=content_slug, status=PublicationStatus.PUBLISHED)
        )
    except ContentVersion.DoesNotExist as exc:
        raise ContentUnavailable("Published practice content was not found.") from exc
    now = timezone.now()
    guest_token = None
    session_fields: dict = {"user": user if user and user.is_authenticated else None}
    if session_fields["user"] is None:
        guest_token = secrets.token_urlsafe(32)
        session_fields.update(
            guest_token_hash=_token_hash(guest_token),
            guest_expires_at=now + timedelta(hours=24),
        )
    deadline = None
    if mode == SessionMode.PRACTICE:
        deadline = now + timedelta(seconds=time_limit_seconds)
    session = AssessmentSession.objects.create(
        mode=mode,
        deadline_at=deadline,
        **session_fields,
    )
    SessionItem.objects.create(
        session=session,
        content_version=version,
        order=1,
        snapshot=_snapshot(version),
    )
    return StartedSession(session=session, guest_token=guest_token)


def authorize_session(session: AssessmentSession, *, user, guest_token: str) -> None:
    if session.user_id:
        if not user or not user.is_authenticated or user.pk != session.user_id:
            raise SessionAccessDenied("This session belongs to another learner.")
        return
    if session.guest_expires_at and session.guest_expires_at <= timezone.now():
        raise GuestAccessExpired("Guest access has expired. Create an account to save progress.")
    supplied_hash = _token_hash(guest_token) if guest_token else ""
    if not secrets.compare_digest(supplied_hash, session.guest_token_hash):
        raise SessionAccessDenied("A valid guest session token is required.")


def _payload_hash(*, choice_id: int | None, expected_revision: int) -> str:
    payload = json.dumps(
        {"choice_id": choice_id, "expected_revision": expected_revision},
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode()).hexdigest()


@transaction.atomic
def save_response(
    *,
    session: AssessmentSession,
    question_id: int,
    choice_id: int | None,
    expected_revision: int,
    idempotency_key: UUID,
) -> tuple[Response, bool]:
    locked = AssessmentSession.objects.select_for_update().get(pk=session.pk)
    if locked.state != SessionState.ACTIVE:
        raise SessionNotActive("Submitted sessions cannot be changed.")
    if locked.deadline_at and locked.deadline_at <= timezone.now():
        raise SessionDeadlinePassed("The practice time limit has ended. Submit for results.")

    item = locked.items.select_related("content_version").get()
    try:
        question = Question.objects.get(pk=question_id, content_version=item.content_version)
    except Question.DoesNotExist as exc:
        raise InvalidAnswer("Question is not part of this session.") from exc
    choice = None
    if choice_id is not None:
        try:
            choice = question.choices.get(pk=choice_id)
        except Choice.DoesNotExist as exc:
            raise InvalidAnswer("Choice is not part of this question.") from exc

    response = Response.objects.select_for_update().filter(
        session_item=item, question=question
    ).first()
    payload_hash = _payload_hash(
        choice_id=choice_id,
        expected_revision=expected_revision,
    )
    if response and response.last_idempotency_key == idempotency_key:
        if response.last_payload_hash != payload_hash:
            raise IdempotencyConflict("The idempotency key was reused with different data.")
        return response, True

    current_revision = response.revision if response else 0
    if expected_revision != current_revision:
        raise StaleRevision(
            f"Expected revision {expected_revision}; current is {current_revision}."
        )
    if response is None:
        response = Response(session_item=item, question=question)
    response.selected_choice = choice
    response.revision = current_revision + 1
    response.last_idempotency_key = idempotency_key
    response.last_payload_hash = payload_hash
    response.full_clean()
    response.save()
    return response, False


@transaction.atomic
def submit_session(session: AssessmentSession) -> ObjectiveResult:
    locked = AssessmentSession.objects.select_for_update().get(pk=session.pk)
    if locked.state == SessionState.SUBMITTED:
        return locked.objective_result

    item = locked.items.get()
    responses = {
        response.question_id: response
        for response in item.responses.select_related("selected_choice")
    }
    outcomes = []
    raw_correct = 0
    questions = item.content_version.questions.prefetch_related("choices")
    for question in questions:
        response = responses.get(question.id)
        selected_id = response.selected_choice_id if response else None
        correct_choice = next(choice for choice in question.choices.all() if choice.is_correct)
        is_correct = selected_id == correct_choice.id
        raw_correct += int(is_correct)
        outcomes.append(
            {
                "question_id": question.id,
                "selected_choice_id": selected_id,
                "correct_choice_id": correct_choice.id,
                "is_correct": is_correct,
                "evidence": question.evidence,
                "explanation": question.explanation,
                "choice_explanations": {
                    str(choice.id): choice.explanation for choice in question.choices.all()
                },
            }
        )
    result = ObjectiveResult.objects.create(
        session=locked,
        raw_correct=raw_correct,
        raw_possible=len(outcomes),
        outcomes=outcomes,
    )
    locked.state = SessionState.SUBMITTED
    locked.submitted_at = timezone.now()
    locked.save(update_fields=["state", "submitted_at", "last_activity_at"])
    return result
