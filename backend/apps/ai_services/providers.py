"""Deterministic fake and live OpenAI provider adapters."""

from __future__ import annotations

import base64
import json
from pathlib import Path

from django.conf import settings

from .contracts import ProviderError, ProviderResult
from .prompts import (
    COACH_DEVELOPER_PROMPT,
    CONTENT_DEVELOPER_PROMPT,
    EXEMPLAR_DEVELOPER_PROMPT,
    FEEDBACK_DEVELOPER_PROMPT,
)
from .schemas import CONTENT_DRAFT_SCHEMA, EXEMPLAR_SCHEMA, FEEDBACK_SCHEMA


class FakeProvider:
    name = "fake"

    def _feedback(self, payload: dict, *, delivery_label: str) -> ProviderResult:
        response = str(payload.get("response") or payload.get("transcript") or "")
        evidence = response[:120].strip() or "No usable response text was available."
        dimensions = []
        for key, label in (
            ("content_coherence", "Content/Coherence"),
            ("vocabulary", "Vocabulary"),
            ("delivery", delivery_label),
            ("task_fulfillment", "Task Fulfillment"),
        ):
            dimensions.append(
                {
                    "key": key,
                    "rating": 2,
                    "evidence": evidence,
                    "next_step": f"Review and strengthen {label.lower()} in one focused retry.",
                }
            )
        return ProviderResult(
            {
                "overall_summary": "A deterministic development estimate was generated.",
                "dimensions": dimensions,
                "strengths": ["A complete practice attempt was submitted."],
                "priorities": ["Add precise support and review the task instructions."],
                "estimated_level_low": 5,
                "estimated_level_high": 7,
                "confidence": "low",
                "disclaimer": "AI-assisted practice estimate — not an official CELPIP score.",
                "pattern_check": [
                    {
                        "step": step["label"],
                        "followed": index == 0,
                        "note": "Development check of this step.",
                    }
                    for index, step in enumerate(
                        (payload.get("answer_pattern") or {}).get("steps", [])
                    )
                ],
                "level_twelve_exemplar": {
                    "response": (
                        "Thank you for raising this matter. I would address it promptly by "
                        "confirming the key details, proposing a practical solution, and "
                        "following up with a clear next step. This approach is respectful, "
                        "specific, and focused on the requested outcome."
                    ),
                    "why_it_is_strong": (
                        "This model response is fully developed, clear, and purposefully "
                        "organized. It demonstrates qualities associated with the highest "
                        "practice band; it is not an official CELPIP score."
                    ),
                    "highlights": [
                        {
                            "excerpt": "raising this matter",
                            "why_it_matters": (
                                "Acknowledges the situation with an appropriate, "
                                "audience-aware tone."
                            ),
                        },
                        {
                            "excerpt": "confirming the key details",
                            "why_it_matters": "Shows a precise and logical first action.",
                        },
                        {
                            "excerpt": "proposing a practical solution",
                            "why_it_matters": (
                                "Addresses the task with concrete support rather than a "
                                "vague promise."
                            ),
                        },
                    ],
                },
            },
            external_id="fake-response",
        )

    def evaluate_writing(self, payload: dict) -> ProviderResult:
        return self._feedback(payload, delivery_label="Readability")

    def grade_text(self, payload: dict) -> ProviderResult:
        label = "Listenability" if payload.get("skill") == "speaking" else "Readability"
        return self._feedback(payload, delivery_label=label)

    def evaluate_speaking(self, audio_path: Path, payload: dict) -> ProviderResult:
        transcript = f"Development transcript for {audio_path.name}."
        result = self._feedback(
            payload | {"transcript": transcript}, delivery_label="Listenability"
        )
        return ProviderResult(result.payload | {"transcript": transcript}, result.external_id)

    def generate_exemplar(self, payload: dict) -> ProviderResult:
        exemplar = self._feedback(payload, delivery_label="Readability").payload[
            "level_twelve_exemplar"
        ]
        steps = (payload.get("answer_pattern") or {}).get("steps", [])
        openings = ["Thank you for raising", "I would address it", "This approach is"]
        exemplar["pattern_map"] = [
            {"step": step["label"], "excerpt": opening}
            for step, opening in zip(steps, openings, strict=False)
        ]
        return ProviderResult(exemplar, "fake-exemplar")

    def coach_reply(self, payload: dict) -> ProviderResult:
        skill = str(payload.get("skill") or "general")
        focus = {
            "listening": (
                "Take notes on purpose, speaker changes, and the detail that answers the question."
            ),
            "reading": (
                "Locate the evidence first, then eliminate choices that go beyond the passage."
            ),
            "writing": (
                "State one clear position, support it with specific details, and finish with a "
                "purposeful close."
            ),
            "speaking": (
                "Use a simple structure, keep moving, and support each point with one concrete "
                "example."
            ),
            "general": (
                "Choose one skill, practise a short timed response, and review one weakness "
                "immediately."
            ),
        }.get(
            skill,
            "Choose one skill and make the next practice attempt specific and measurable.",
        )
        message = (
            f"For {skill} practice, start with the task requirement rather than a memorized "
            "template. "
            f"1. {focus} 2. Check that every sentence has a clear job. "
            "3. Review one weak point before starting another attempt. "
            "Next action: answer one prompt in 10 minutes, then compare it with the task "
            "instructions."
        )
        return ProviderResult({"message": message}, external_id="fake-coach")

    def generate_content(self, payload: dict) -> ProviderResult:
        topic = str(payload.get("topic", "Canadian community services"))
        task_type = str(payload.get("task_type", "reading_correspondence"))
        return ProviderResult(
            {
                "slug": f"ai-draft-{task_type}-{abs(hash(topic)) % 100000}",
                "title": f"Draft Practice Set: {topic}",
                "topic": topic,
                "difficulty": int(payload.get("difficulty", 2)),
                "estimated_level": 7,
                "instructions": "Read the original practice material and answer each question.",
                "stimulus": {
                    "type": "article",
                    "title": topic,
                    "body": f"Original draft about {topic}.",
                },
                "learning_notes": "Editorial review required before use.",
                "questions": [
                    {
                        "stem": "What is the main purpose of this draft?",
                        "skill_focus": "purpose",
                        "evidence": f"The text focuses on {topic}.",
                        "explanation": "The central topic establishes the purpose.",
                        "choices": [
                            {
                                "text": f"To explain {topic}",
                                "is_correct": True,
                                "explanation": "Matches the focus.",
                            },
                            {
                                "text": "To advertise a private sale",
                                "is_correct": False,
                                "explanation": "No sale is described.",
                            },
                            {
                                "text": "To report a sports result",
                                "is_correct": False,
                                "explanation": "No sport is discussed.",
                            },
                            {
                                "text": "To cancel an appointment",
                                "is_correct": False,
                                "explanation": "No appointment is mentioned.",
                            },
                        ],
                    }
                ],
            },
            external_id="fake-content",
        )

    def generate_image(self, prompt: str) -> bytes:
        del prompt
        return b"fake-image"

    def synthesize_speech(self, text: str, *, voice: str) -> bytes:
        del text, voice
        return b"fake-audio"


# Reasoning tokens count toward max_output_tokens, so grading at a higher
# effort needs more headroom than the visible JSON alone would.
FEEDBACK_MAX_OUTPUT_TOKENS = 4000


class OpenAIProvider:
    name = "openai"

    def __init__(self, client=None):
        if not settings.OPENAI_API_KEY and client is None:
            raise ProviderError(
                "not_configured", "OPENAI_API_KEY is not configured.", retryable=False
            )
        if client is None:
            try:
                from openai import OpenAI
            except ImportError as exc:
                raise ProviderError(
                    "sdk_missing", "The OpenAI SDK is not installed.", retryable=False
                ) from exc
            client = OpenAI(api_key=settings.OPENAI_API_KEY, timeout=90, max_retries=2)
        self.client = client

    @staticmethod
    def _usage(response) -> dict:
        usage = getattr(response, "usage", None)
        if usage is None:
            return {}
        return usage.model_dump() if hasattr(usage, "model_dump") else {}

    def _structured(
        self,
        *,
        developer_prompt: str,
        payload: dict,
        schema: dict,
        name: str,
        max_output_tokens: int | None = None,
        effort: str | None = None,
    ) -> ProviderResult:
        # Reasoning effort and an output cap bound how long one job can run.
        # Both are omitted when unset so a blank effort setting falls back to
        # the model's own default rather than an invalid empty value.
        effort = settings.AI_REASONING_EFFORT if effort is None else effort
        extra: dict = {}
        if effort:
            extra["reasoning"] = {"effort": effort}
        if max_output_tokens:
            extra["max_output_tokens"] = max_output_tokens
        try:
            response = self.client.responses.create(
                model=settings.OPENAI_TEXT_MODEL,
                store=False,
                input=[
                    {"role": "developer", "content": developer_prompt},
                    {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
                ],
                text={
                    "format": {
                        "type": "json_schema",
                        "name": name,
                        "strict": True,
                        "schema": schema,
                    }
                },
                **extra,
            )
            parsed = json.loads(response.output_text)
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            raise ProviderError(
                "invalid_output", "OpenAI returned malformed structured output.", retryable=False
            ) from exc
        except Exception as exc:
            raise ProviderError("provider_error", "OpenAI could not complete the request.") from exc
        return ProviderResult(parsed, getattr(response, "id", ""), self._usage(response))

    def evaluate_writing(self, payload: dict) -> ProviderResult:
        return self.grade_text(payload)

    def grade_text(self, payload: dict) -> ProviderResult:
        """Grade a written response or a speaking transcript on the same scale."""
        skill = "speaking" if payload.get("skill") == "speaking" else "writing"
        return self._structured(
            developer_prompt=FEEDBACK_DEVELOPER_PROMPT,
            payload=payload,
            schema=FEEDBACK_SCHEMA,
            name=f"celpip_{skill}_feedback",
            max_output_tokens=FEEDBACK_MAX_OUTPUT_TOKENS,
            effort=settings.AI_FEEDBACK_REASONING_EFFORT,
        )

    def evaluate_speaking(self, audio_path: Path, payload: dict) -> ProviderResult:
        try:
            with audio_path.open("rb") as recording:
                transcript_response = self.client.audio.transcriptions.create(
                    model=settings.OPENAI_TRANSCRIBE_MODEL,
                    file=recording,
                    response_format="text",
                )
            transcript = (
                transcript_response
                if isinstance(transcript_response, str)
                else getattr(transcript_response, "text", "")
            )
        except Exception as exc:
            raise ProviderError(
                "transcription_error", "OpenAI could not transcribe the recording."
            ) from exc
        timing = {"transcript": transcript}
        duration_ms = payload.get("recording_duration_ms") or 0
        if duration_ms > 0:
            # Pace is the one delivery signal a transcript can't show on its own.
            timing["speech_rate_words_per_minute"] = round(
                len(transcript.split()) * 60000 / duration_ms
            )
        result = self.grade_text(payload | timing)
        return ProviderResult(
            result.payload | {"transcript": transcript}, result.external_id, result.usage
        )

    def generate_exemplar(self, payload: dict) -> ProviderResult:
        return self._structured(
            developer_prompt=EXEMPLAR_DEVELOPER_PROMPT, payload=payload,
            schema=EXEMPLAR_SCHEMA, name="celpip_response_exemplar",
            max_output_tokens=1600,
        )

    def coach_reply(self, payload: dict) -> ProviderResult:
        skill = str(payload.get("skill") or "general")
        message = str(payload.get("message") or "").strip()
        history = payload.get("history") if isinstance(payload.get("history"), list) else []
        input_items = [
            {
                "role": item.get("role"),
                "content": str(item.get("content") or ""),
            }
            for item in history
            if isinstance(item, dict) and item.get("role") in {"user", "assistant"}
        ]
        input_items.append(
            {
                "role": "user",
                "content": f"Practice focus: {skill}\n\nLearner question: {message}",
            }
        )
        extra: dict = {}
        if settings.AI_REASONING_EFFORT:
            extra["reasoning"] = {"effort": settings.AI_REASONING_EFFORT}
        try:
            response = self.client.responses.create(
                model=settings.OPENAI_TEXT_MODEL,
                store=False,
                instructions=COACH_DEVELOPER_PROMPT,
                input=input_items,
                max_output_tokens=900,
                **extra,
            )
            reply = response.output_text
        except Exception as exc:
            raise ProviderError("provider_error", "OpenAI could not answer the learner.") from exc
        return ProviderResult(
            {"message": reply}, getattr(response, "id", ""), self._usage(response)
        )

    def generate_content(self, payload: dict) -> ProviderResult:
        return self._structured(
            developer_prompt=CONTENT_DEVELOPER_PROMPT,
            payload=payload,
            schema=CONTENT_DRAFT_SCHEMA,
            name="celpip_content_draft",
        )

    def generate_image(self, prompt: str) -> bytes:
        try:
            result = self.client.images.generate(
                model=settings.OPENAI_IMAGE_MODEL,
                prompt=prompt,
                size="1536x1024",
                quality="medium",
                output_format="png",
            )
            return base64.b64decode(result.data[0].b64_json)
        except Exception as exc:
            raise ProviderError("image_error", "OpenAI could not generate the image.") from exc

    def synthesize_speech(self, text: str, *, voice: str) -> bytes:
        try:
            response = self.client.audio.speech.create(
                model=settings.OPENAI_TTS_MODEL,
                voice=voice,
                input=text,
                response_format="mp3",
            )
            return response.read()
        except Exception as exc:
            raise ProviderError("speech_error", "OpenAI could not generate the audio.") from exc


def get_provider():
    if settings.AI_PROVIDER == "fake":
        return FakeProvider()
    if settings.AI_PROVIDER == "openai":
        return OpenAIProvider()
    raise ProviderError(
        "unknown_provider", f"Unknown AI provider: {settings.AI_PROVIDER}", retryable=False
    )
