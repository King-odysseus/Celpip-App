from django.urls import path

from .views import (
    AnalyticsView,
    DashboardView,
    HistoryView,
    MistakeDetailView,
    MistakeListView,
    ProgressView,
    RecommendationView,
    StudyPlanView,
    StudyTaskView,
)

app_name = "learning"

urlpatterns = [
    path("me/dashboard/", DashboardView.as_view(), name="dashboard"),
    path("me/analytics/", AnalyticsView.as_view(), name="analytics"),
    path("me/history/", HistoryView.as_view(), name="history"),
    path("me/recommendation/", RecommendationView.as_view(), name="recommendation"),
    path("me/progress/", ProgressView.as_view(), name="progress"),
    path("me/mistakes/", MistakeListView.as_view(), name="mistakes"),
    path("me/mistakes/<int:mistake_id>/", MistakeDetailView.as_view(), name="mistake-detail"),
    path("me/study-plan/", StudyPlanView.as_view(), name="study-plan"),
    path("me/study-plan/tasks/<int:task_id>/", StudyTaskView.as_view(), name="study-task"),
]
