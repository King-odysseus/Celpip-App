"""Short-lived access grants and byte-range private audio streaming."""
from __future__ import annotations

import re

from django.http import StreamingHttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.assessments.models import AssessmentSession
from apps.assessments.services import AssessmentError, authorize_session

from .models import MediaAsset
from .services import (
    MediaAccessError,
    PlaybackLimitReached,
    grant_audio_access,
    private_media_path,
    verify_stream_token,
)

RANGE_PATTERN = re.compile(r"bytes=(\d*)-(\d*)$")


def media_error(exc: MediaAccessError) -> Response:
    response_status = (
        status.HTTP_409_CONFLICT
        if isinstance(exc, PlaybackLimitReached)
        else status.HTTP_403_FORBIDDEN
    )
    return Response(
        {"code": exc.code, "message": str(exc), "fields": {}},
        status=response_status,
    )


class AudioAccessView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, session_id, asset_id):
        session = get_object_or_404(AssessmentSession, pk=session_id)
        asset = get_object_or_404(MediaAsset, pk=asset_id)
        try:
            authorize_session(
                session,
                user=request.user,
                guest_token=request.headers.get("X-Guest-Token", ""),
            )
            access = grant_audio_access(session=session, asset=asset)
        except AssessmentError as exc:
            return Response(
                {"code": exc.code, "message": str(exc), "fields": {}},
                status=status.HTTP_403_FORBIDDEN,
            )
        except MediaAccessError as exc:
            return media_error(exc)
        return Response(
            {
                "url": access.url,
                "expires_in_seconds": access.expires_in_seconds,
                "plays_remaining": access.plays_remaining,
            }
        )


class AudioStreamView(APIView):
    permission_classes = [AllowAny]
    authentication_classes: list = []

    def get(self, request, asset_id):
        try:
            asset = verify_stream_token(
                asset_id=asset_id,
                token=request.query_params.get("token", ""),
            )
        except MediaAccessError as exc:
            return media_error(exc)
        path = private_media_path(asset.storage_key)
        size = path.stat().st_size
        start, end, response_status = 0, size - 1, status.HTTP_200_OK
        range_header = request.headers.get("Range", "")
        match = RANGE_PATTERN.fullmatch(range_header)
        if match:
            start = int(match.group(1) or 0)
            end = min(int(match.group(2) or size - 1), size - 1)
            if start > end or start >= size:
                return Response(status=status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE)
            response_status = status.HTTP_206_PARTIAL_CONTENT

        response = StreamingHttpResponse(
            _file_chunks(path, start=start, length=end - start + 1),
            status=response_status,
            content_type=asset.mime_type,
        )
        response["Accept-Ranges"] = "bytes"
        response["Content-Length"] = str(end - start + 1)
        response["Cache-Control"] = "private, no-store"
        response["Content-Disposition"] = 'inline; filename="practice-audio"'
        if response_status == status.HTTP_206_PARTIAL_CONTENT:
            response["Content-Range"] = f"bytes {start}-{end}/{size}"
        return response


def _file_chunks(path, *, start: int, length: int, chunk_size: int = 64 * 1024):
    with path.open("rb") as media_file:
        media_file.seek(start)
        remaining = length
        while remaining:
            data = media_file.read(min(chunk_size, remaining))
            if not data:
                break
            remaining -= len(data)
            yield data
