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
from .models import AICoachConversation
from .serializers import (
    AICoachConversationSerializer,
    AICoachMessageCreateSerializer,
    AICoachMessageSerializer,
)
from .services import (
    ask_coach,
    clear_coach_messages,
    coach_conversations,
    coach_messages,
    feedback_history,
    feedback_payload,
    latest_coach_conversation,
    retry_response_exemplar,
)
from .throttling import AICoachRateThrottle


class AIFeedbackView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, session_id):
        session = self._authorized_session(request, session_id)
        if isinstance(session, Response):
            return session
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

    @staticmethod
    def _authorized_session(request, session_id):
        session = get_object_or_404(AssessmentSession, pk=session_id)
        try:
            authorize_session(
                session,
                user=request.user,
                guest_token=request.headers.get("X-Guest-Token", ""),
            )
        except AssessmentError as exc:
            return error_response(exc)
        return session

    def post(self, request, session_id):
        session = self._authorized_session(request, session_id)
        if isinstance(session, Response):
            return session
        if _mock_embargoed(session):
            return Response(
                {
                    "code": "mock_results_embargoed",
                    "message": "AI feedback is released after all four mock components finish.",
                    "fields": {},
                },
                status=status.HTTP_409_CONFLICT,
            )
        try:
            retry_response_exemplar(session.items.get())
        except ValidationError as exc:
            return Response(
                {"code": "example_not_retryable", "message": exc.messages[0], "fields": {}},
                status=status.HTTP_409_CONFLICT,
            )
        return Response(feedback_payload(session.items.get()), status=status.HTTP_202_ACCEPTED)


class AIFeedbackHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({"results": feedback_history(request.user)})


def _conversation_payload(user, conversation):
    return {
        "conversation": (
            AICoachConversationSerializer(conversation).data if conversation else None
        ),
        "messages": AICoachMessageSerializer(
            coach_messages(user, conversation) if conversation else [], many=True
        ).data,
    }


class AICoachView(APIView):
    """Read the latest chat, ask a question, or clear all AI Coach history."""

    permission_classes = [IsAuthenticated]
    throttle_classes = [AICoachRateThrottle]

    def get_throttles(self):
        """Rate-limit provider calls, not reading or clearing saved messages."""
        if self.request.method != "POST":
            return []
        return super().get_throttles()

    def get(self, request):
        return Response(
            _conversation_payload(request.user, latest_coach_conversation(request.user))
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
        data = dict(serializer.validated_data)
        conversation_id = data.pop("conversation_id", None)
        conversation = None
        if conversation_id is not None:
            conversation = get_object_or_404(
                AICoachConversation, pk=conversation_id, user=request.user
            )
        try:
            learner_message, coach_message = ask_coach(
                user=request.user, conversation=conversation, **data
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
                "conversation": AICoachConversationSerializer(
                    learner_message.conversation
                ).data,
                "user_message": AICoachMessageSerializer(learner_message).data,
                "coach_message": AICoachMessageSerializer(coach_message).data,
            },
            status=status.HTTP_201_CREATED,
        )

    def delete(self, request):
        clear_coach_messages(request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


class AICoachConversationListView(APIView):
    """List the learner's saved AI Coach chats for the history page."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(
            {
                "results": AICoachConversationSerializer(
                    coach_conversations(request.user), many=True
                ).data
            }
        )


class AICoachConversationDetailView(APIView):
    """Reopen or delete one of the learner's saved AI Coach chats."""

    permission_classes = [IsAuthenticated]

    def get(self, request, conversation_id):
        conversation = get_object_or_404(
            AICoachConversation, pk=conversation_id, user=request.user
        )
        return Response(_conversation_payload(request.user, conversation))

    def delete(self, request, conversation_id):
        conversation = get_object_or_404(
            AICoachConversation, pk=conversation_id, user=request.user
        )
        conversation.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
