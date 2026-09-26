"""Transport validation for the account-scoped AI Coach."""

from __future__ import annotations

from rest_framework import serializers

from .models import AICoachConversation, AICoachMessage

COACH_SKILL_CHOICES = ("general", "listening", "reading", "writing", "speaking")


class AICoachMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = AICoachMessage
        fields = ("id", "role", "content", "skill", "created_at")
        read_only_fields = fields


class AICoachConversationSerializer(serializers.ModelSerializer):
    message_count = serializers.SerializerMethodField()

    class Meta:
        model = AICoachConversation
        fields = ("id", "title", "skill", "message_count", "created_at", "updated_at")
        read_only_fields = fields

    def get_message_count(self, conversation) -> int:
        annotated = getattr(conversation, "message_count", None)
        return annotated if annotated is not None else conversation.messages.count()


class AICoachMessageCreateSerializer(serializers.Serializer):
    message = serializers.CharField(max_length=8000, trim_whitespace=True)
    skill = serializers.ChoiceField(choices=COACH_SKILL_CHOICES, default="general")
    conversation_id = serializers.UUIDField(required=False, allow_null=True)
