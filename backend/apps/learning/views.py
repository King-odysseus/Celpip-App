from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .analytics import (
    HISTORY_PAGE_SIZE_DEFAULT,
    analytics_payload,
    history_payload,
    recommendation_payload,
)
from .models import MistakeRecord, MistakeState, StudyPlan, StudyTaskState
from .services import (
    dashboard_payload,
    plan_payload,
    progress_payload,
    regenerate_plan,
    set_task_state,
    study_plan_consistency,
)


def _query_integer(request, key: str, default: int) -> tuple[int, Response | None]:
    raw = request.query_params.get(key)
    if raw is None:
        return default, None
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return default, Response(
            {"code": "invalid_query", "message": f"{key} must be a positive integer.", "fields": {key: raw}},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if value < 1:
        return default, Response(
            {"code": "invalid_query", "message": f"{key} must be a positive integer.", "fields": {key: raw}},
            status=status.HTTP_400_BAD_REQUEST,
        )
    return value, None


def _mistake_payload(mistake: MistakeRecord) -> dict:
    return {
        "id": mistake.pk,
        "skill": mistake.skill,
        "task_type": mistake.task_type_id,
        "task_title": mistake.task_type.title,
        "stem": mistake.stem_snapshot,
        "selected": mistake.selected_snapshot,
        "correct": mistake.correct_snapshot,
        "explanation": mistake.explanation_snapshot,
        "occurrences": mistake.occurrences,
        "state": mistake.state,
        "first_seen_at": mistake.first_seen_at,
        "last_seen_at": mistake.last_seen_at,
        "resolved_at": mistake.resolved_at,
    }


class ProgressView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(progress_payload(request.user))


class DashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(dashboard_payload(request.user))


class AnalyticsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(analytics_payload(request.user))


class HistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        page, error = _query_integer(request, "page", 1)
        if error is not None:
            return error
        page_size, error = _query_integer(
            request, "page_size", HISTORY_PAGE_SIZE_DEFAULT
        )
        if error is not None:
            return error
        return Response(history_payload(request.user, page=page, page_size=page_size))


class RecommendationView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(recommendation_payload(request.user))


class MistakeListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = MistakeRecord.objects.filter(user=request.user).select_related("task_type")
        state_filter = request.query_params.get("state")
        skill_filter = request.query_params.get("skill")
        if state_filter in MistakeState.values:
            queryset = queryset.filter(state=state_filter)
        if skill_filter:
            queryset = queryset.filter(skill=skill_filter)
        return Response(
            {"count": queryset.count(), "results": [_mistake_payload(item) for item in queryset]}
        )


class MistakeDetailView(APIView):
    permission_classes = [IsAuthenticated]

    class InputSerializer(serializers.Serializer):
        state = serializers.ChoiceField(choices=MistakeState.choices)

    def patch(self, request, mistake_id):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        mistake = get_object_or_404(MistakeRecord, pk=mistake_id, user=request.user)
        mistake.state = serializer.validated_data["state"]
        mistake.resolved_at = timezone.now() if mistake.state == MistakeState.RESOLVED else None
        mistake.save(update_fields=["state", "resolved_at"])
        return Response(_mistake_payload(mistake))


class StudyPlanView(APIView):
    permission_classes = [IsAuthenticated]

    class InputSerializer(serializers.Serializer):
        name = serializers.CharField(max_length=120, allow_blank=True, required=False)

    def _active_plan(self, request):
        plan = StudyPlan.objects.filter(user=request.user, is_active=True).first()
        if plan is None:
            plan = regenerate_plan(request.user)
        return plan

    def get(self, request):
        plan = self._active_plan(request)
        return Response(
            {
                **plan_payload(plan),
                "consistency": study_plan_consistency(request.user),
            }
        )

    def post(self, request):
        plan = regenerate_plan(request.user)
        return Response(
            {
                **plan_payload(plan),
                "consistency": study_plan_consistency(request.user),
            },
            status=status.HTTP_201_CREATED,
        )

    def patch(self, request):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        plan = self._active_plan(request)
        if "name" in serializer.validated_data:
            plan.name = serializer.validated_data["name"]
            plan.save(update_fields=["name"])
        return Response(
            {
                **plan_payload(plan),
                "consistency": study_plan_consistency(request.user),
            }
        )


class StudyTaskView(APIView):
    permission_classes = [IsAuthenticated]

    class InputSerializer(serializers.Serializer):
        state = serializers.ChoiceField(choices=StudyTaskState.choices)

    def patch(self, request, task_id):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        task = set_task_state(
            user=request.user,
            task_id=task_id,
            state=serializer.validated_data["state"],
        )
        return Response({"id": task.pk, "state": task.state, "completed_at": task.completed_at})
