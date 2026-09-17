from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.assessments.models import AssessmentSession
from apps.assessments.services import AssessmentError, authorize_session
from apps.assessments.views import _mock_embargoed, error_response

from .contracts import ProviderError
from .serializers import AICoachMessageCreateSerializer, AICoachMessageSerializer
from .services import (
    ask_coach,
    clear_coach_messages,
    coach_messages,
    feedback_history,
    feedback_payload,
)
from .throttling import AICoachRateThrottle


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


class AIFeedbackHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({"results": feedback_history(request.user)})


class AICoachView(APIView):
    """Read, append to, or clear the authenticated learner's AI Coach chat."""

    permission_classes = [IsAuthenticated]
    throttle_classes = [AICoachRateThrottle]

    def get_throttles(self):
        """Rate-limit provider calls, not reading or clearing saved messages."""
        if self.request.method != "POST":
            return []
        return super().get_throttles()

    def get(self, request):
        return Response(
            {"messages": AICoachMessageSerializer(coach_messages(request.user), many=True).data}
        )

    def post(self, request):
        serializer = AICoachMessageCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {
                    "code": "invalid_input",
                    "message": "Check your question and try again.",
                    "fields": serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            learner_message, coach_message = ask_coach(
                user=request.user, **serializer.validated_data
            )
        except ValidationError as exc:
            return Response(
                {
                    "code": "invalid_input",
                    "message": exc.messages[0],
                    "fields": {},
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except ProviderError as exc:
            return Response(
                {
                    "code": exc.code,
                    "message": str(exc),
                    "fields": {},
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response(
            {
                "user_message": AICoachMessageSerializer(learner_message).data,
                "coach_message": AICoachMessageSerializer(coach_message).data,
            },
            status=status.HTTP_201_CREATED,
        )

    def delete(self, request):
        clear_coach_messages(request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)
