"""Transport validation for the account-scoped AI Coach."""

from __future__ import annotations

from rest_framework import serializers

from .models import AICoachMessage

COACH_SKILL_CHOICES = ("general", "listening", "reading", "writing", "speaking")


class AICoachMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = AICoachMessage
        fields = ("id", "role", "content", "skill", "created_at")
        read_only_fields = fields


class AICoachMessageCreateSerializer(serializers.Serializer):
    message = serializers.CharField(max_length=2000, trim_whitespace=True)
    skill = serializers.ChoiceField(choices=COACH_SKILL_CHOICES, default="general")
