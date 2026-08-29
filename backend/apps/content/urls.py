from django.urls import path

from .views import (
    ContentCatalogView,
    ContentDetailView,
    ListeningCatalogView,
    ListeningDetailView,
    SpeakingCatalogView,
    SpeakingDetailView,
    TaskTypeListView,
    WritingCatalogView,
    WritingDetailView,
)

app_name = "content"

urlpatterns = [
    path("content/task-types/", TaskTypeListView.as_view(), name="task-types"),
    path("content/reading/", ContentCatalogView.as_view(), name="catalog"),
    path("content/reading/<slug:slug>/", ContentDetailView.as_view(), name="detail"),
    path("content/listening/", ListeningCatalogView.as_view(), name="listening-catalog"),
    path(
        "content/listening/<slug:slug>/",
        ListeningDetailView.as_view(),
        name="listening-detail",
    ),
    path("content/writing/", WritingCatalogView.as_view(), name="writing-catalog"),
    path(
        "content/writing/<slug:slug>/",
        WritingDetailView.as_view(),
        name="writing-detail",
    ),
    path("content/speaking/", SpeakingCatalogView.as_view(), name="speaking-catalog"),
    path(
        "content/speaking/<slug:slug>/",
        SpeakingDetailView.as_view(),
        name="speaking-detail",
    ),
]
