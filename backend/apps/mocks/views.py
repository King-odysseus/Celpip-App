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
        focus_mode = serializers.ChoiceField(
            choices=("balanced", "recommended", "custom"), required=False
        )
        skills = serializers.ListField(
            child=serializers.ChoiceField(choices=("listening", "reading", "writing", "speaking")),
            required=False,
            allow_empty=False,
        )
        task_types = serializers.ListField(
            child=serializers.CharField(max_length=64), required=False, allow_empty=False
        )
        scheduled_for = serializers.DateField(required=False)

        def validate(self, attrs):
            if attrs["scope"] == FULL_LENGTH_SCOPE and (
                any(key in attrs for key in ("skills", "task_types"))
                or attrs.get("focus_mode") not in (None, "balanced")
            ):
                raise serializers.ValidationError(
                    "Full simulations keep the fixed CELPIP-General structure; tailor a compact mock instead."
                )
            if attrs.get("focus_mode") == "custom" and not (
                attrs.get("skills") or attrs.get("task_types")
            ):
                raise serializers.ValidationError("Choose one or more skills or task types.")
            if attrs.get("scheduled_for") and attrs["scope"] != FULL_LENGTH_SCOPE:
                raise serializers.ValidationError("Only a full simulation can be scheduled for a specific day.")
            return attrs

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
            data = serializer.validated_data
            focus = None
            if data["scope"] == COMPACT_SCOPE:
                focus = {
                    "mode": data.get("focus_mode", "balanced"),
                    "skills": data.get("skills", []),
                    "task_types": data.get("task_types", []),
                }
            attempt = create_attempt(
                request.user,
                scope=data["scope"],
                focus=focus,
                scheduled_for=data.get("scheduled_for"),
            )
        except MockError as exc:
            return _error(exc)
        return Response(attempt_payload(attempt), status=status.HTTP_201_CREATED)


class MockDetailView(APIView):
    permission_classes = [IsAuthenticated]

    class ScheduleSerializer(serializers.Serializer):
        scheduled_for = serializers.DateField(allow_null=True)

    def get(self, request, attempt_id):
        try:
            attempt = refresh_attempt(attempt_id, request.user)
        except MockAttempt.DoesNotExist:
            attempt = get_object_or_404(MockAttempt, pk=attempt_id, user=request.user)
        return Response(attempt_payload(attempt))

    def patch(self, request, attempt_id):
        serializer = self.ScheduleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        attempt = get_object_or_404(MockAttempt, pk=attempt_id, user=request.user)
        if attempt.scope != FULL_LENGTH_SCOPE or attempt.state != "ready":
            return Response(
                {"code": "schedule_locked", "message": "Only a ready full simulation can be rescheduled.", "fields": {}},
                status=status.HTTP_409_CONFLICT,
            )
        attempt.scheduled_for = serializer.validated_data["scheduled_for"]
        attempt.save(update_fields=["scheduled_for", "updated_at"])
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
