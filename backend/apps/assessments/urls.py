from django.urls import path

from .views import (
    ResponseSaveView,
    SessionDetailView,
    SessionListCreateView,
    SessionResultView,
    SessionSubmitView,
    SpeakingAudioView,
    SpeakingDetailView,
    SpeakingSubmitView,
    WritingDetailView,
    WritingSubmitView,
)

app_name = "assessments"

urlpatterns = [
    path("sessions/", SessionListCreateView.as_view(), name="session-create"),
    path("sessions/<uuid:session_id>/", SessionDetailView.as_view(), name="session-detail"),
    path(
        "sessions/<uuid:session_id>/responses/<int:question_id>/",
        ResponseSaveView.as_view(),
        name="response-save",
    ),
    path(
        "sessions/<uuid:session_id>/submit/",
        SessionSubmitView.as_view(),
        name="session-submit",
    ),
    path(
        "sessions/<uuid:session_id>/results/",
        SessionResultView.as_view(),
        name="session-results",
    ),
    path(
        "sessions/<uuid:session_id>/writing/",
        WritingDetailView.as_view(),
        name="writing-detail",
    ),
    path(
        "sessions/<uuid:session_id>/writing/submit/",
        WritingSubmitView.as_view(),
        name="writing-submit",
    ),
    path(
        "sessions/<uuid:session_id>/speaking/",
        SpeakingDetailView.as_view(),
        name="speaking-detail",
    ),
    path(
        "sessions/<uuid:session_id>/speaking/submit/",
        SpeakingSubmitView.as_view(),
        name="speaking-submit",
    ),
    path(
        "sessions/<uuid:session_id>/speaking/audio/",
        SpeakingAudioView.as_view(),
        name="speaking-audio",
    ),
]
