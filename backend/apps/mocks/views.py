from django.shortcuts import get_object_or_404
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import MockAttempt
from .services import (
    COMPACT_SCOPE,
    FULL_LENGTH_SCOPE,
    InvalidTransition,
    MockError,
    ResultsEmbargoed,
    advance_attempt,
    attempt_payload,
    create_attempt,
    refresh_attempt,
    results_payload,
    start_attempt,
)


def _error(exc: MockError) -> Response:
    response_status = (
        status.HTTP_409_CONFLICT
        if isinstance(exc, (InvalidTransition, ResultsEmbargoed))
        else status.HTTP_400_BAD_REQUEST
    )
    return Response({"code": exc.code, "message": str(exc), "fields": {}}, status=response_status)


class MockListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    class CreateSerializer(serializers.Serializer):
        scope = serializers.ChoiceField(
            choices=[COMPACT_SCOPE, FULL_LENGTH_SCOPE], default=COMPACT_SCOPE, required=False
        )

    def get(self, request):
        attempts = MockAttempt.objects.filter(user=request.user).prefetch_related("tasks")
        return Response(
            {
                "count": attempts.count(),
                "results": [attempt_payload(attempt, include_tasks=False) for attempt in attempts],
            }
        )

    def post(self, request):
        serializer = self.CreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            attempt = create_attempt(request.user, scope=serializer.validated_data["scope"])
        except MockError as exc:
            return _error(exc)
        return Response(attempt_payload(attempt), status=status.HTTP_201_CREATED)


class MockDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, attempt_id):
        try:
            attempt = refresh_attempt(attempt_id, request.user)
        except MockAttempt.DoesNotExist:
            attempt = get_object_or_404(MockAttempt, pk=attempt_id, user=request.user)
        return Response(attempt_payload(attempt))


class MockStartView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, attempt_id):
        try:
            attempt, replayed = start_attempt(attempt_id, request.user)
        except MockAttempt.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        except MockError as exc:
            return _error(exc)
        return Response(attempt_payload(attempt) | {"replayed": replayed})


class MockAdvanceView(APIView):
    permission_classes = [IsAuthenticated]

    class InputSerializer(serializers.Serializer):
        # The compact mock has exactly 20 tasks; the full-length simulation
        # assembles more (a section may combine several content versions to
        # reach its official question count). This is only an input sanity
        # bound — real order validation happens against the attempt's actual
        # task list in advance_attempt().
        expected_order = serializers.IntegerField(min_value=1, max_value=200)

    def post(self, request, attempt_id):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            attempt, replayed = advance_attempt(
                attempt_id,
                request.user,
                expected_order=serializer.validated_data["expected_order"],
            )
        except MockAttempt.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        except MockError as exc:
            return _error(exc)
        return Response(attempt_payload(attempt) | {"replayed": replayed})


class MockResultsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, attempt_id):
        attempt = get_object_or_404(
            MockAttempt.objects.prefetch_related("tasks"), pk=attempt_id, user=request.user
        )
        try:
            return Response(results_payload(attempt))
        except MockError as exc:
            return _error(exc)
