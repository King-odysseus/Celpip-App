"""Deterministic fake and live OpenAI provider adapters."""

from __future__ import annotations

import base64
import json
from pathlib import Path

from django.conf import settings

from .contracts import ProviderError, ProviderResult
from .prompts import CONTENT_DEVELOPER_PROMPT, FEEDBACK_DEVELOPER_PROMPT
from .schemas import CONTENT_DRAFT_SCHEMA, FEEDBACK_SCHEMA


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
            },
            external_id="fake-response",
        )

    def evaluate_writing(self, payload: dict) -> ProviderResult:
        return self._feedback(payload, delivery_label="Readability")

    def evaluate_speaking(self, audio_path: Path, payload: dict) -> ProviderResult:
        transcript = f"Development transcript for {audio_path.name}."
        result = self._feedback(
            payload | {"transcript": transcript}, delivery_label="Listenability"
        )
        return ProviderResult(result.payload | {"transcript": transcript}, result.external_id)

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
        self, *, developer_prompt: str, payload: dict, schema: dict, name: str
    ) -> ProviderResult:
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
        return self._structured(
            developer_prompt=FEEDBACK_DEVELOPER_PROMPT,
            payload=payload,
            schema=FEEDBACK_SCHEMA,
            name="celpip_writing_feedback",
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
        result = self._structured(
            developer_prompt=FEEDBACK_DEVELOPER_PROMPT,
            payload=payload | {"transcript": transcript},
            schema=FEEDBACK_SCHEMA,
            name="celpip_speaking_feedback",
        )
        return ProviderResult(
            result.payload | {"transcript": transcript}, result.external_id, result.usage
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
