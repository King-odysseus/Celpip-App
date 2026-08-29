"""Input validation and safe session/result representations."""
from rest_framework import serializers

from .models import SessionMode


class StartSessionSerializer(serializers.Serializer):
    content_slug = serializers.SlugField(max_length=120)
    mode = serializers.ChoiceField(choices=SessionMode.choices)
    time_limit_seconds = serializers.IntegerField(
        min_value=60,
        max_value=3600,
        default=900,
        help_text="Learner-selected practice timer; not an official per-task limit.",
    )


class SaveResponseSerializer(serializers.Serializer):
    selected_choice_id = serializers.IntegerField(min_value=1, allow_null=True)
    expected_revision = serializers.IntegerField(min_value=0)


def public_snapshot(snapshot: dict, *, include_learning_notes: bool) -> dict:
    result = {
        key: value
        for key, value in snapshot.items()
        if key not in {"questions", "learning_notes"}
    }
    if include_learning_notes:
        result["learning_notes"] = snapshot.get("learning_notes", "")
    result["questions"] = [
        {
            key: value
            for key, value in question.items()
            if key not in {"evidence", "explanation", "choices"}
        }
        | {
            "choices": [
                {
                    key: value
                    for key, value in choice.items()
                    if key not in {"is_correct", "explanation"}
                }
                for choice in question["choices"]
            ]
        }
        for question in snapshot["questions"]
    ]
    return result
