"""Small provider interface so domain code never imports a vendor SDK."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class ProviderResult:
    payload: dict
    external_id: str = ""
    usage: dict = field(default_factory=dict)


class AIProvider(Protocol):
    name: str

    def evaluate_writing(self, payload: dict) -> ProviderResult: ...

    def evaluate_speaking(self, audio_path: Path, payload: dict) -> ProviderResult: ...

    def generate_content(self, payload: dict) -> ProviderResult: ...

    def generate_image(self, prompt: str) -> bytes: ...

    def synthesize_speech(self, text: str, *, voice: str) -> bytes: ...


class ProviderError(RuntimeError):
    """A safe provider failure; raw secrets and response bodies stay out of errors."""

    def __init__(self, code: str, message: str, *, retryable: bool = True):
        super().__init__(message)
        self.code = code
        self.retryable = retryable
