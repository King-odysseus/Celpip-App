"""Thin HTTP endpoints for starting, resuming, saving, and scoring sessions."""
from __future__ import annotations

from uuid import UUID

from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response as ApiResponse
from rest_framework.views import APIView

from apps.content.models import Choice, Question

from .models import AssessmentSession, SessionMode, SessionState
from .serializers import SaveResponseSerializer, StartSessionSerializer, public_snapshot
from .services import (
    AssessmentError,
    GuestAccessExpired,
    IdempotencyConflict,
    SessionAccessDenied,
    SessionDeadlinePassed,
    SessionNotActive,
    StaleRevision,
    authorize_session,
    save_response,
    start_session,
    submit_session,
)


def error_response(exc: AssessmentError) -> ApiResponse:
    response_status = status.HTTP_400_BAD_REQUEST
    if isinstance(exc, (SessionAccessDenied, GuestAccessExpired)):
        response_status = status.HTTP_403_FORBIDDEN
    elif isinstance(
        exc,
        (StaleRevision, IdempotencyConflict, SessionNotActive, SessionDeadlinePassed),
    ):
        response_status = status.HTTP_409_CONFLICT
    return ApiResponse(
        {"code": exc.code, "message": str(exc), "fields": {}},
        status=response_status,
    )


def _session_for_request(request, session_id) -> AssessmentSession:
    session = get_object_or_404(
        AssessmentSession.objects.prefetch_related("items__responses"),
        pk=session_id,
    )
    authorize_session(
        session,
        user=request.user,
        guest_token=request.headers.get("X-Guest-Token", ""),
    )
    return session


def _session_payload(session: AssessmentSession) -> dict:
    item = session.items.get()
    return {
        "id": str(session.id),
        "mode": session.mode,
        "state": session.state,
        "started_at": session.started_at,
        "deadline_at": session.deadline_at,
        "submitted_at": session.submitted_at,
        "server_now": timezone.now(),
        "is_guest": session.user_id is None,
        "content": public_snapshot(
            item.snapshot,
            include_learning_notes=session.mode == SessionMode.LEARN,
        ),
        "responses": [
            {
                "question_id": response.question_id,
                "selected_choice_id": response.selected_choice_id,
                "revision": response.revision,
                "saved_at": response.saved_at,
            }
            for response in item.responses.all()
        ],
    }


class SessionListCreateView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = StartSessionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            started = start_session(user=request.user, **serializer.validated_data)
        except AssessmentError as exc:
            return error_response(exc)
        payload = _session_payload(started.session)
        if started.guest_token:
            payload["guest_token"] = started.guest_token
            payload["guest_expires_at"] = started.session.guest_expires_at
        return ApiResponse(payload, status=status.HTTP_201_CREATED)


class SessionDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, session_id):
        try:
            session = _session_for_request(request, session_id)
        except AssessmentError as exc:
            return error_response(exc)
        return ApiResponse(_session_payload(session))


class ResponseSaveView(APIView):
    permission_classes = [AllowAny]

    def put(self, request, session_id, question_id):
        serializer = SaveResponseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        raw_key = request.headers.get("Idempotency-Key", "")
        try:
            idempotency_key = UUID(raw_key)
        except ValueError:
            return ApiResponse(
                {
                    "code": "invalid_idempotency_key",
                    "message": "Idempotency-Key must be a UUID.",
                    "fields": {},
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            session = _session_for_request(request, session_id)
            saved, replayed = save_response(
                session=session,
                question_id=question_id,
                choice_id=serializer.validated_data["selected_choice_id"],
                expected_revision=serializer.validated_data["expected_revision"],
                idempotency_key=idempotency_key,
            )
        except AssessmentError as exc:
            return error_response(exc)

        payload = {
            "question_id": saved.question_id,
            "selected_choice_id": saved.selected_choice_id,
            "revision": saved.revision,
            "saved_at": saved.saved_at,
            "replayed": replayed,
        }
        if session.mode == SessionMode.LEARN and saved.selected_choice_id:
            question = Question.objects.prefetch_related("choices").get(pk=saved.question_id)
            selected = Choice.objects.get(pk=saved.selected_choice_id)
            correct = next(choice for choice in question.choices.all() if choice.is_correct)
            payload["feedback"] = {
                "is_correct": selected.id == correct.id,
                "correct_choice_id": correct.id,
                "evidence": question.evidence,
                "explanation": question.explanation,
                "selected_choice_explanation": selected.explanation,
            }
        return ApiResponse(payload)


class SessionSubmitView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, session_id):
        try:
            session = _session_for_request(request, session_id)
            was_submitted = session.state == SessionState.SUBMITTED
            result = submit_session(session)
        except AssessmentError as exc:
            return error_response(exc)
        return ApiResponse(_result_payload(result) | {"replayed": was_submitted})


class SessionResultView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, session_id):
        try:
            session = _session_for_request(request, session_id)
        except AssessmentError as exc:
            return error_response(exc)
        if session.state != SessionState.SUBMITTED:
            return ApiResponse(
                {
                    "code": "results_not_released",
                    "message": "Practice corrections are released after submission.",
                    "fields": {},
                },
                status=status.HTTP_409_CONFLICT,
            )
        return ApiResponse(_result_payload(session.objective_result))


def _result_payload(result) -> dict:
    return {
        "session_id": str(result.session_id),
        "raw_correct": result.raw_correct,
        "raw_possible": result.raw_possible,
        "accuracy_percent": round(100 * result.raw_correct / result.raw_possible),
        "outcomes": result.outcomes,
        "scored_at": result.scored_at,
        "score_label": "Practice accuracy",
        "disclaimer": "This is practice feedback, not an official CELPIP score.",
    }
