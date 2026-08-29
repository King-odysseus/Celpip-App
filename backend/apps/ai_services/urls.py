from django.urls import path

from .views import AIFeedbackView

app_name = "ai_services"

urlpatterns = [
    path(
        "sessions/<uuid:session_id>/ai-feedback/",
        AIFeedbackView.as_view(),
        name="session-ai-feedback",
    ),
]
