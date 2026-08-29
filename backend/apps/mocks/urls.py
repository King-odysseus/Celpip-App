from django.urls import path

from .views import (
    MockAdvanceView,
    MockDetailView,
    MockListCreateView,
    MockResultsView,
    MockStartView,
)

app_name = "mocks"

urlpatterns = [
    path("mocks/", MockListCreateView.as_view(), name="list-create"),
    path("mocks/<uuid:attempt_id>/", MockDetailView.as_view(), name="detail"),
    path("mocks/<uuid:attempt_id>/start/", MockStartView.as_view(), name="start"),
    path("mocks/<uuid:attempt_id>/advance/", MockAdvanceView.as_view(), name="advance"),
    path("mocks/<uuid:attempt_id>/results/", MockResultsView.as_view(), name="results"),
]
