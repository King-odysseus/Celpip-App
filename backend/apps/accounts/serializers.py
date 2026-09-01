"""Transport-layer validation for account endpoints.

Serializers validate and shape JSON only. All state changes live in
:mod:`apps.accounts.services`.
"""
from __future__ import annotations

from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from rest_framework import serializers

from .models import (
    MAX_TARGET_LEVEL,
    MIN_TARGET_LEVEL,
    LearnerProfile,
    User,
)
from .services import MIN_PASSWORD_LENGTH


class RegisterSerializer(serializers.Serializer):
    """Exactly two fields — no confirmation, no mandatory verification."""

    identifier = serializers.CharField(max_length=254, trim_whitespace=True)
    password = serializers.CharField(
        min_length=MIN_PASSWORD_LENGTH,
        max_length=128,
        style={"input_type": "password"},
        trim_whitespace=False,
    )


class LoginSerializer(serializers.Serializer):
    identifier = serializers.CharField(max_length=254, trim_whitespace=True)
    password = serializers.CharField(
        max_length=128, style={"input_type": "password"}, trim_whitespace=False
    )


class RecoveryResetSerializer(serializers.Serializer):
    identifier = serializers.CharField(max_length=254, trim_whitespace=True)
    recovery_code = serializers.CharField(max_length=128, trim_whitespace=True)
    new_password = serializers.CharField(
        min_length=MIN_PASSWORD_LENGTH,
        max_length=128,
        style={"input_type": "password"},
        trim_whitespace=False,
    )


class UserSerializer(serializers.ModelSerializer):
    """Read-only identity for the authenticated user."""

    class Meta:
        model = User
        fields = ["id", "identifier", "email", "date_joined"]
        read_only_fields = fields


class AccountDeleteSerializer(serializers.Serializer):
    """Confirmation for self-service deletion.

    Exactly one of the two loose-model credentials is required: the account
    password, or the still-unused one-time recovery code. Neither is returned
    or stored; the service verifies them and answers generically.
    """

    password = serializers.CharField(
        max_length=128,
        style={"input_type": "password"},
        trim_whitespace=False,
        required=False,
        allow_blank=True,
    )
    recovery_code = serializers.CharField(
        max_length=128,
        trim_whitespace=True,
        required=False,
        allow_blank=True,
    )

    def validate(self, attrs: dict) -> dict:
        if not (attrs.get("password") or attrs.get("recovery_code")):
            raise serializers.ValidationError(
                "Provide your password or recovery code to delete the account."
            )
        return attrs


def _validate_weekdays(value: list[int]) -> list[int]:
    if not isinstance(value, list):
        raise serializers.ValidationError("Expected a list of ISO weekday numbers.")
    cleaned: list[int] = []
    for day in value:
        if not isinstance(day, int) or isinstance(day, bool) or not 1 <= day <= 7:
            raise serializers.ValidationError(
                "Weekdays must be integers from 1 (Mon) to 7 (Sun)."
            )
        if day not in cleaned:
            cleaned.append(day)
    return sorted(cleaned)


class LearnerProfileSerializer(serializers.ModelSerializer):
    identifier = serializers.CharField(source="user.identifier", read_only=True)
    preferred_weekdays = serializers.ListField(
        child=serializers.IntegerField(), required=False
    )
    mock_weekdays = serializers.ListField(
        child=serializers.IntegerField(), required=False
    )

    class Meta:
        model = LearnerProfile
        fields = [
            "identifier",
            "exam_date",
            "target_level",
            "target_listening",
            "target_reading",
            "target_writing",
            "target_speaking",
            "daily_minutes",
            "mock_interval_days",
            "mock_schedule_mode",
            "preferred_weekdays",
            "mock_weekdays",
            "timezone",
            "practice_narration_voice",
            "preferred_audio_provider",
            "updated_at",
        ]
        read_only_fields = ["identifier", "updated_at"]
        extra_kwargs = {
            "target_level": {
                "min_value": MIN_TARGET_LEVEL,
                "max_value": MAX_TARGET_LEVEL,
            },
            "target_listening": {
                "min_value": MIN_TARGET_LEVEL,
                "max_value": MAX_TARGET_LEVEL,
            },
            "target_reading": {
                "min_value": MIN_TARGET_LEVEL,
                "max_value": MAX_TARGET_LEVEL,
            },
            "target_writing": {
                "min_value": MIN_TARGET_LEVEL,
                "max_value": MAX_TARGET_LEVEL,
            },
            "target_speaking": {
                "min_value": MIN_TARGET_LEVEL,
                "max_value": MAX_TARGET_LEVEL,
            },
            "daily_minutes": {"min_value": 5, "max_value": 600},
            "mock_interval_days": {"min_value": 1, "max_value": 30},
        }

    def validate_preferred_weekdays(self, value: list[int]) -> list[int]:
        return _validate_weekdays(value)

    def validate_mock_weekdays(self, value: list[int]) -> list[int]:
        cleaned = _validate_weekdays(value)
        if not cleaned:
            raise serializers.ValidationError("Choose at least one mock-test day.")
        return cleaned

    def validate_timezone(self, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError):
            raise serializers.ValidationError(
                "Use a valid IANA timezone such as Europe/London."
            ) from None
        return value
