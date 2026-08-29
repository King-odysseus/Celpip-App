"""Thin auth and profile API views.

Each view validates transport input, calls a service or token helper, then
serialises the result. Business rules and state changes live in
:mod:`apps.accounts.services` and :mod:`apps.accounts.tokens`.
"""
from __future__ import annotations

from django.middleware.csrf import get_token
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError

from . import services, tokens
from .export import build_export
from .serializers import (
    AccountDeleteSerializer,
    LearnerProfileSerializer,
    LoginSerializer,
    RecoveryResetSerializer,
    RegisterSerializer,
    UserSerializer,
)
from .throttling import (
    LoginRateThrottle,
    RecoveryRateThrottle,
    RegisterRateThrottle,
)


def error(code: str, message: str, status_code: int, fields: dict | None = None) -> Response:
    """Build the platform's consistent error envelope."""
    return Response(
        {"code": code, "message": message, "fields": fields or {}},
        status=status_code,
    )


def _validation_error(serializer_errors: dict) -> Response:
    return error(
        "invalid_input",
        "Some fields were invalid.",
        status.HTTP_400_BAD_REQUEST,
        fields=serializer_errors,
    )


class CsrfView(APIView):
    """Sets the CSRF cookie so the SPA can send the matching header later."""

    permission_classes = [AllowAny]
    authentication_classes: list = []

    def get(self, request: Request) -> Response:
        get_token(request)  # ensures the CSRF cookie is set on the response
        return Response({"detail": "CSRF cookie set."})


class RegisterView(APIView):
    permission_classes = [AllowAny]
    authentication_classes: list = []
    throttle_classes = [RegisterRateThrottle]

    def post(self, request: Request) -> Response:
        tokens.enforce_csrf(request)
        serializer = RegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return _validation_error(serializer.errors)
        data = serializer.validated_data
        try:
            result = services.register_user(data["identifier"], data["password"])
        except services.AccountError as exc:
            code_status = (
                status.HTTP_409_CONFLICT
                if isinstance(exc, services.IdentifierTaken)
                else status.HTTP_400_BAD_REQUEST
            )
            return error(exc.code, exc.message, code_status)

        pair = tokens.issue_tokens_for_user(result.user)
        response = Response(
            {
                "access": pair.access,
                "user": UserSerializer(result.user).data,
                "recovery_code": result.recovery_code,
            },
            status=status.HTTP_201_CREATED,
        )
        tokens.set_refresh_cookie(response, pair.refresh)
        return response


class LoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes: list = []
    throttle_classes = [LoginRateThrottle]

    def post(self, request: Request) -> Response:
        tokens.enforce_csrf(request)
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return _validation_error(serializer.errors)
        data = serializer.validated_data
        try:
            user = services.authenticate_user(data["identifier"], data["password"])
        except services.InvalidCredentials as exc:
            return error(exc.code, exc.message, status.HTTP_401_UNAUTHORIZED)

        pair = tokens.issue_tokens_for_user(user)
        response = Response({"access": pair.access, "user": UserSerializer(user).data})
        tokens.set_refresh_cookie(response, pair.refresh)
        return response


class RefreshView(APIView):
    """Rotate the refresh cookie and return a fresh access token.

    Reads the refresh token from the HttpOnly cookie the browser sends, so it
    is CSRF-protected. Rotation blacklists the previous refresh token.
    """

    permission_classes = [AllowAny]
    authentication_classes: list = []

    def post(self, request: Request) -> Response:
        tokens.enforce_csrf(request)
        refresh_token = tokens.read_refresh_cookie(request)
        if not refresh_token:
            return error(
                "no_refresh_token",
                "No refresh token was provided.",
                status.HTTP_401_UNAUTHORIZED,
            )
        try:
            pair = tokens.rotate_refresh_token(refresh_token)
        except TokenError:
            response = error(
                "invalid_refresh_token",
                "The session has expired. Please sign in again.",
                status.HTTP_401_UNAUTHORIZED,
            )
            tokens.clear_refresh_cookie(response)
            return response

        response = Response({"access": pair.access})
        tokens.set_refresh_cookie(response, pair.refresh)
        return response


class LogoutView(APIView):
    """Revoke the refresh token and clear the cookie."""

    permission_classes = [AllowAny]
    authentication_classes: list = []

    def post(self, request: Request) -> Response:
        tokens.enforce_csrf(request)
        refresh_token = tokens.read_refresh_cookie(request)
        if refresh_token:
            try:
                tokens.blacklist_refresh_token(refresh_token)
            except TokenError:
                # Already invalid/expired; clearing the cookie is enough.
                pass
        response = Response(status=status.HTTP_205_RESET_CONTENT)
        tokens.clear_refresh_cookie(response)
        return response


class RecoveryResetView(APIView):
    permission_classes = [AllowAny]
    authentication_classes: list = []
    throttle_classes = [RecoveryRateThrottle]

    def post(self, request: Request) -> Response:
        tokens.enforce_csrf(request)
        serializer = RecoveryResetSerializer(data=request.data)
        if not serializer.is_valid():
            return _validation_error(serializer.errors)
        data = serializer.validated_data
        try:
            new_code = services.reset_password_with_recovery_code(
                data["identifier"], data["recovery_code"], data["new_password"]
            )
        except services.InvalidPassword as exc:
            return error(exc.code, exc.message, status.HTTP_400_BAD_REQUEST)
        except services.InvalidCredentials as exc:
            return error(exc.code, exc.message, status.HTTP_400_BAD_REQUEST)
        return Response({"recovery_code": new_code})


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        return Response(UserSerializer(request.user).data)

    def delete(self, request: Request) -> Response:
        serializer = AccountDeleteSerializer(data=request.data)
        if not serializer.is_valid():
            return _validation_error(serializer.errors)
        data = serializer.validated_data
        try:
            services.delete_account(
                request.user,
                password=data.get("password"),
                recovery_code=data.get("recovery_code"),
            )
        except (services.ConfirmationRequired, services.InvalidCredentials) as exc:
            return error(exc.code, exc.message, status.HTTP_400_BAD_REQUEST)
        # The account is gone: drop the refresh cookie so the SPA cannot try to
        # rotate a token for a deleted user.
        response = Response(status=status.HTTP_204_NO_CONTENT)
        tokens.clear_refresh_cookie(response)
        return response


class AccountExportView(APIView):
    """Export the authenticated learner's own data (privacy-safe JSON)."""

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        return Response(build_export(request.user))


class ProfileView(APIView):
    """Read or update the authenticated learner's profile.

    Ownership is implicit: the profile is always the requesting user's own,
    fetched via the reverse one-to-one relation.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        return Response(LearnerProfileSerializer(request.user.profile).data)

    def patch(self, request: Request) -> Response:
        serializer = LearnerProfileSerializer(
            request.user.profile, data=request.data, partial=True
        )
        if not serializer.is_valid():
            return _validation_error(serializer.errors)
        services.update_profile(request.user.profile, **serializer.validated_data)
        return Response(LearnerProfileSerializer(request.user.profile).data)
