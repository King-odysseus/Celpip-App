from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.assessments.models import AssessmentSession
from apps.assessments.services import AssessmentError, authorize_session
from apps.assessments.views import _mock_embargoed, error_response

from .services import feedback_payload


class AIFeedbackView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, session_id):
        session = get_object_or_404(AssessmentSession, pk=session_id)
        try:
            authorize_session(
                session,
                user=request.user,
                guest_token=request.headers.get("X-Guest-Token", ""),
            )
        except AssessmentError as exc:
            return error_response(exc)
        if _mock_embargoed(session):
            return Response(
                {
                    "code": "mock_results_embargoed",
                    "message": "AI feedback is released after all four mock components finish.",
                    "fields": {},
                },
                status=status.HTTP_409_CONFLICT,
            )
        return Response(feedback_payload(session.items.get()))
