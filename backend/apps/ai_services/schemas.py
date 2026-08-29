"""Versioned JSON schemas and validation for model outputs."""

from __future__ import annotations

from .contracts import ProviderError

RUBRIC_KEYS = ("content_coherence", "vocabulary", "delivery", "task_fulfillment")

FEEDBACK_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "overall_summary": {"type": "string"},
        "dimensions": {
            "type": "array",
            "minItems": 4,
            "maxItems": 4,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "key": {"type": "string", "enum": list(RUBRIC_KEYS)},
                    "rating": {"type": "integer", "minimum": 1, "maximum": 4},
                    "evidence": {"type": "string"},
                    "next_step": {"type": "string"},
                },
                "required": ["key", "rating", "evidence", "next_step"],
            },
        },
        "strengths": {"type": "array", "items": {"type": "string"}, "maxItems": 3},
        "priorities": {"type": "array", "items": {"type": "string"}, "maxItems": 3},
        "estimated_level_low": {"type": "integer", "minimum": 1, "maximum": 12},
        "estimated_level_high": {"type": "integer", "minimum": 1, "maximum": 12},
        "confidence": {"type": "string", "enum": ["low", "medium", "high"]},
        "disclaimer": {"type": "string"},
    },
    "required": [
        "overall_summary",
        "dimensions",
        "strengths",
        "priorities",
        "estimated_level_low",
        "estimated_level_high",
        "confidence",
        "disclaimer",
    ],
}

CONTENT_DRAFT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "slug": {"type": "string"},
        "title": {"type": "string"},
        "topic": {"type": "string"},
        "difficulty": {"type": "integer", "minimum": 1, "maximum": 3},
        "estimated_level": {"type": "integer", "minimum": 1, "maximum": 12},
        "instructions": {"type": "string"},
        "stimulus": {"type": "object"},
        "learning_notes": {"type": "string"},
        "questions": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "stem": {"type": "string"},
                    "skill_focus": {
                        "type": "string",
                        "enum": ["gist", "detail", "inference", "vocabulary", "purpose"],
                    },
                    "evidence": {"type": "string"},
                    "explanation": {"type": "string"},
                    "choices": {
                        "type": "array",
                        "minItems": 4,
                        "maxItems": 4,
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {
                                "text": {"type": "string"},
                                "is_correct": {"type": "boolean"},
                                "explanation": {"type": "string"},
                            },
                            "required": ["text", "is_correct", "explanation"],
                        },
                    },
                },
                "required": ["stem", "skill_focus", "evidence", "explanation", "choices"],
            },
        },
    },
    "required": [
        "slug",
        "title",
        "topic",
        "difficulty",
        "estimated_level",
        "instructions",
        "stimulus",
        "learning_notes",
        "questions",
    ],
}


def validate_feedback(payload: dict) -> dict:
    if not isinstance(payload, dict):
        raise ProviderError(
            "invalid_output", "The provider returned invalid feedback.", retryable=False
        )
    dimensions = payload.get("dimensions")
    if not isinstance(dimensions, list) or len(dimensions) != 4:
        raise ProviderError(
            "invalid_output", "Feedback must contain four dimensions.", retryable=False
        )
    keys = [item.get("key") for item in dimensions if isinstance(item, dict)]
    if set(keys) != set(RUBRIC_KEYS) or len(keys) != 4:
        raise ProviderError(
            "invalid_output", "Feedback dimension keys are invalid.", retryable=False
        )
    low, high = payload.get("estimated_level_low"), payload.get("estimated_level_high")
    if not isinstance(low, int) or not isinstance(high, int) or not (1 <= low <= high <= 12):
        raise ProviderError(
            "invalid_output", "The estimated level range is invalid.", retryable=False
        )
    payload["disclaimer"] = "AI-assisted practice estimate — not an official CELPIP score."
    return payload


def validate_content_draft(payload: dict) -> dict:
    if not isinstance(payload, dict) or not isinstance(payload.get("questions"), list):
        raise ProviderError(
            "invalid_output", "The provider returned an invalid content draft.", retryable=False
        )
    if not payload["questions"]:
        raise ProviderError(
            "invalid_output", "An objective draft needs questions.", retryable=False
        )
    for question in payload["questions"]:
        choices = question.get("choices", []) if isinstance(question, dict) else []
        if len(choices) != 4 or sum(choice.get("is_correct") is True for choice in choices) != 1:
            raise ProviderError(
                "invalid_output",
                "Each question needs four choices and one answer.",
                retryable=False,
            )
    return payload
