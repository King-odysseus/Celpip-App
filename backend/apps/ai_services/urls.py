from django.urls import path

from .views import AICoachView, AIFeedbackHistoryView, AIFeedbackView

app_name = "ai_services"

urlpatterns = [
    path(
        "sessions/<uuid:session_id>/ai-feedback/",
        AIFeedbackView.as_view(),
        name="session-ai-feedback",
    ),
    path(
        "me/ai-feedback/history/",
        AIFeedbackHistoryView.as_view(),
        name="ai-feedback-history",
    ),
    path("me/ai-coach/", AICoachView.as_view(), name="ai-coach"),
]
