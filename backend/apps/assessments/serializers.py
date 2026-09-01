"""Input validation and safe session/result representations."""
from rest_framework import serializers

from .models import SessionMode


class StartSessionSerializer(serializers.Serializer):
    content_slug = serializers.SlugField(max_length=120)
    # Full mocks are assembled via apps.mocks (POST /mocks/), never started
    # directly as a bare timed session.
    mode = serializers.ChoiceField(
        choices=[
            (SessionMode.LEARN, "Learn"),
            (SessionMode.PRACTICE, "Practice"),
            (SessionMode.DIAGNOSTIC, "Diagnostic"),
        ],
    )
    time_limit_seconds = serializers.IntegerField(
        min_value=60,
        max_value=3600,
        default=900,
        help_text="Learner-selected practice timer; not an official per-task limit.",
    )


class SaveResponseSerializer(serializers.Serializer):
    selected_choice_id = serializers.IntegerField(min_value=1, allow_null=True)
    expected_revision = serializers.IntegerField(min_value=0)


class SaveWritingSerializer(serializers.Serializer):
    # Blank is allowed so a learner can autosave an empty or cleared draft.
    text = serializers.CharField(allow_blank=True, trim_whitespace=False)
    expected_revision = serializers.IntegerField(min_value=0)


class SubmitWritingSerializer(serializers.Serializer):
    # Supplying the editor's current text makes final submission atomic even if
    # the last debounced autosave was interrupted or the timer just expired.
    # It remains optional for backward-compatible replay of an autosaved draft.
    text = serializers.CharField(allow_blank=True, trim_whitespace=False, required=False)


class SaveSpeakingSerializer(serializers.Serializer):
    audio = serializers.FileField(allow_empty_file=False)
    duration_ms = serializers.IntegerField(min_value=100, max_value=180_000)
    expected_revision = serializers.IntegerField(min_value=0)


def public_snapshot(snapshot: dict, *, include_learning_notes: bool) -> dict:
    result = {
        key: value
        for key, value in snapshot.items()
        if key not in {"questions", "learning_notes"}
    }
    if include_learning_notes:
        result["learning_notes"] = snapshot.get("learning_notes", "")
    elif isinstance(result.get("stimulus"), dict):
        # Prompt-specific coaching is a Learn-mode aid, not part of a timed
        # practice prompt. Copy before removing it so the frozen snapshot stays
        # unchanged.
        result["stimulus"] = {
            key: value for key, value in result["stimulus"].items() if key != "guidance"
        }
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
