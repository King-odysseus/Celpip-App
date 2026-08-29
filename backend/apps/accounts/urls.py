"""Account routes, mounted under ``/api/v1/``."""
from django.urls import path

from .views import (
    AccountExportView,
    CsrfView,
    LoginView,
    LogoutView,
    MeView,
    ProfileView,
    RecoveryResetView,
    RefreshView,
    RegisterView,
)

app_name = "accounts"

urlpatterns = [
    path("auth/csrf/", CsrfView.as_view(), name="csrf"),
    path("auth/register/", RegisterView.as_view(), name="register"),
    path("auth/login/", LoginView.as_view(), name="login"),
    path("auth/refresh/", RefreshView.as_view(), name="refresh"),
    path("auth/logout/", LogoutView.as_view(), name="logout"),
    path(
        "auth/recovery-code/reset/",
        RecoveryResetView.as_view(),
        name="recovery-reset",
    ),
    path("me/", MeView.as_view(), name="me"),
    path("me/export/", AccountExportView.as_view(), name="export"),
    path("me/profile/", ProfileView.as_view(), name="profile"),
]
