from rest_framework import serializers

from .models import Choice, ContentVersion, Question, TaskType


class TaskTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskType
        fields = [
            "code",
            "skill",
            "title",
            "part_number",
            "description",
            "strategy",
            "common_mistakes",
        ]


class PublicChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Choice
        fields = ["id", "order", "text"]


class PublicQuestionSerializer(serializers.ModelSerializer):
    choices = PublicChoiceSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        fields = ["id", "order", "stem", "skill_focus", "choices"]


class ContentCatalogSerializer(serializers.ModelSerializer):
    slug = serializers.CharField(source="item.slug")
    title = serializers.CharField(source="item.title")
    topic = serializers.CharField(source="item.topic")
    difficulty = serializers.IntegerField(source="item.difficulty")
    estimated_level = serializers.IntegerField(source="item.estimated_level")
    task_type = serializers.CharField(source="item.task_type_id")

    class Meta:
        model = ContentVersion
        fields = [
            "id",
            "slug",
            "version",
            "title",
            "topic",
            "difficulty",
            "estimated_level",
            "task_type",
        ]


class PublicContentSerializer(ContentCatalogSerializer):
    instructions = serializers.CharField()
    stimulus = serializers.JSONField()
    questions = PublicQuestionSerializer(many=True, read_only=True)

    class Meta(ContentCatalogSerializer.Meta):
        fields = ContentCatalogSerializer.Meta.fields + ["instructions", "stimulus", "questions"]
