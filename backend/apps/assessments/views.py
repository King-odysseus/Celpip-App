"""Thin HTTP endpoints for starting, resuming, saving, and scoring sessions."""
from __future__ import annotations

import re
from pathlib import Path
from uuid import UUID

from django.http import HttpResponse, StreamingHttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response as ApiResponse
from rest_framework.views import APIView

from apps.content.models import Choice, Question
from apps.media_assets.models import MediaAsset

from .models import AssessmentSession, SessionMode, SessionState
from .serializers import (
    SaveResponseSerializer,
    SaveSpeakingSerializer,
    SaveWritingSerializer,
    StartSessionSerializer,
    SubmitWritingSerializer,
    public_snapshot,
)
from .services import (
    SPEAKING_RUBRIC_DIMENSIONS,
    WRITING_RUBRIC_DIMENSIONS,
    AssessmentError,
    GuestAccessExpired,
    IdempotencyConflict,
    SessionAccessDenied,
    SessionDeadlinePassed,
    SessionNotActive,
    StaleRevision,
    authorize_session,
    get_speaking_submission,
    get_writing_submission,
    save_response,
    save_speaking,
    save_writing,
    speaking_review_metadata,
    start_session,
    submit_session,
    submit_speaking,
    submit_writing,
    writing_review_metadata,
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
    payload = {
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
    try:
        asset = item.content_version.audio_asset
    except MediaAsset.DoesNotExist:
        asset = None
    if asset:
        payload["audio"] = {
            "asset_id": str(asset.id),
            "duration_ms": asset.duration_ms,
            "voice_label": asset.voice_label,
            "playback_policy": (
                "one_play" if session.mode == SessionMode.PRACTICE else "unlimited_learning"
            ),
        }
    return payload


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
            try:
                payload["feedback"]["transcript"] = (
                    saved.session_item.content_version.audio_asset.transcript
                )
            except MediaAsset.DoesNotExist:
                pass
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


def _submission_payload(submission) -> dict | None:
    if submission is None:
        return None
    return {
        "text": submission.text,
        "word_count": submission.word_count,
        "revision": submission.revision,
        "saved_at": submission.saved_at,
        "submitted_at": submission.submitted_at,
    }


def _writing_payload(session: AssessmentSession, item, submission) -> dict:
    payload = {
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
        "rubric": {"dimensions": WRITING_RUBRIC_DIMENSIONS},
        "submission": _submission_payload(submission),
    }
    if submission is not None and submission.is_submitted:
        payload["review"] = writing_review_metadata(item, submission)
    return payload


class WritingDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, session_id):
        try:
            session = _session_for_request(request, session_id)
            item, submission = get_writing_submission(session)
        except AssessmentError as exc:
            return error_response(exc)
        return ApiResponse(_writing_payload(session, item, submission))

    def put(self, request, session_id):
        serializer = SaveWritingSerializer(data=request.data)
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
            submission, replayed = save_writing(
                session=session,
                text=serializer.validated_data["text"],
                expected_revision=serializer.validated_data["expected_revision"],
                idempotency_key=idempotency_key,
            )
        except AssessmentError as exc:
            return error_response(exc)
        return ApiResponse(_submission_payload(submission) | {"replayed": replayed})


class WritingSubmitView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, session_id):
        serializer = SubmitWritingSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        try:
            session = _session_for_request(request, session_id)
            was_submitted = session.state == SessionState.SUBMITTED
            submission = submit_writing(
                session, final_text=serializer.validated_data.get("text")
            )
            item, _ = get_writing_submission(session)
        except AssessmentError as exc:
            return error_response(exc)
        payload = writing_review_metadata(item, submission)
        payload |= {
            "session_id": str(session.id),
            "state": SessionState.SUBMITTED,
            "submission": _submission_payload(submission),
            "replayed": was_submitted,
        }
        return ApiResponse(payload)


def _speaking_submission_payload(session_id, submission) -> dict | None:
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
        "audio_url": f"/api/v1/sessions/{session_id}/speaking/audio/",
    }


def _speaking_payload(session, item, submission) -> dict:
    payload = {
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
        "rubric": {"dimensions": SPEAKING_RUBRIC_DIMENSIONS},
        "submission": _speaking_submission_payload(session.id, submission),
    }
    if submission is not None and submission.is_submitted:
        payload["review"] = speaking_review_metadata(submission)
    return payload


class SpeakingDetailView(APIView):
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request, session_id):
        try:
            session = _session_for_request(request, session_id)
            item, submission = get_speaking_submission(session)
        except AssessmentError as exc:
            return error_response(exc)
        return ApiResponse(_speaking_payload(session, item, submission))

    def put(self, request, session_id):
        serializer = SaveSpeakingSerializer(data=request.data)
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
            submission, replayed = save_speaking(
                session=session,
                audio=serializer.validated_data["audio"],
                duration_ms=serializer.validated_data["duration_ms"],
                expected_revision=serializer.validated_data["expected_revision"],
                idempotency_key=idempotency_key,
            )
        except AssessmentError as exc:
            return error_response(exc)
        return ApiResponse(
            _speaking_submission_payload(session.id, submission) | {"replayed": replayed}
        )


class SpeakingSubmitView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, session_id):
        try:
            session = _session_for_request(request, session_id)
            was_submitted = session.state == SessionState.SUBMITTED
            submission = submit_speaking(session)
        except AssessmentError as exc:
            return error_response(exc)
        return ApiResponse(
            speaking_review_metadata(submission)
            | {
                "session_id": str(session.id),
                "state": SessionState.SUBMITTED,
                "submission": _speaking_submission_payload(session.id, submission),
                "replayed": was_submitted,
            }
        )


SPEAKING_RANGE_PATTERN = re.compile(r"bytes=(\d*)-(\d*)$")


def _recording_range(value: str, size: int):
    if not value:
        return 0, size - 1, status.HTTP_200_OK
    match = SPEAKING_RANGE_PATTERN.fullmatch(value)
    if not match:
        return None
    first, last = match.groups()
    if not first and not last:
        return None
    if not first:
        suffix = int(last)
        if suffix <= 0:
            return None
        start, end = max(0, size - suffix), size - 1
    else:
        start = int(first)
        end = min(int(last) if last else size - 1, size - 1)
    if start >= size or start > end:
        return None
    return start, end, status.HTTP_206_PARTIAL_CONTENT


class SpeakingAudioView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, session_id):
        return self._response(request, session_id, include_body=True)

    def head(self, request, session_id):
        return self._response(request, session_id, include_body=False)

    def _response(self, request, session_id, *, include_body: bool):
        try:
            session = _session_for_request(request, session_id)
            _, submission = get_speaking_submission(session)
        except AssessmentError as exc:
            return error_response(exc)
        if submission is None or not submission.audio.name:
            return ApiResponse(
                {
                    "code": "missing_recording",
                    "message": "No speaking recording is available.",
                    "fields": {},
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        path = Path(submission.audio.path)
        size = path.stat().st_size
        parsed = _recording_range(request.headers.get("Range", ""), size)
        if parsed is None:
            response = HttpResponse(status=status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE)
            response["Content-Range"] = f"bytes */{size}"
            return response
        start, end, response_status = parsed
        if include_body:
            response = StreamingHttpResponse(
                _private_file_chunks(path, start=start, length=end - start + 1),
                status=response_status,
                content_type=submission.mime_type,
            )
        else:
            response = HttpResponse(status=response_status, content_type=submission.mime_type)
        response["Accept-Ranges"] = "bytes"
        response["Content-Length"] = str(end - start + 1)
        response["Cache-Control"] = "private, no-store"
        response["X-Content-Type-Options"] = "nosniff"
        response["Content-Disposition"] = (
            f'inline; filename="speaking-response.{submission.container}"'
        )
        if response_status == status.HTTP_206_PARTIAL_CONTENT:
            response["Content-Range"] = f"bytes {start}-{end}/{size}"
        return response


def _private_file_chunks(path, *, start: int, length: int, chunk_size: int = 64 * 1024):
    with path.open("rb") as recording:
        recording.seek(start)
        remaining = length
        while remaining:
            data = recording.read(min(chunk_size, remaining))
            if not data:
                break
            remaining -= len(data)
            yield data


def _result_payload(result) -> dict:
    payload = {
        "session_id": str(result.session_id),
        "raw_correct": result.raw_correct,
        "raw_possible": result.raw_possible,
        "accuracy_percent": round(100 * result.raw_correct / result.raw_possible),
        "outcomes": result.outcomes,
        "scored_at": result.scored_at,
        "score_label": "Practice accuracy",
        "disclaimer": "This is practice feedback, not an official CELPIP score.",
    }
    item = result.session.items.get()
    try:
        payload["transcript"] = item.content_version.audio_asset.transcript
    except MediaAsset.DoesNotExist:
        pass
    return payload
