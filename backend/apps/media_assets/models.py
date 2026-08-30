"""Metadata for private audio; binary files are never public media URLs."""
from __future__ import annotations

import uuid

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.assessments.models import AssessmentSession
from apps.content.models import ContentVersion


class MediaStatus(models.TextChoices):
    PENDING = "pending", "Pending validation"
    READY = "ready", "Ready"
    REJECTED = "rejected", "Rejected"


class RenditionProvider(models.TextChoices):
    """Remote speech vendors that can produce an alternative audio rendition."""

    OPENAI = "openai", "OpenAI"
    AZURE = "azure", "Azure"


class MediaAsset(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    content_version = models.OneToOneField(
        ContentVersion,
        on_delete=models.PROTECT,
        related_name="audio_asset",
    )
    storage_key = models.CharField(max_length=240, unique=True)
    mime_type = models.CharField(max_length=80)
    byte_size = models.PositiveIntegerField(validators=[MaxValueValidator(20 * 1024 * 1024)])
    duration_ms = models.PositiveIntegerField(
        validators=[MinValueValidator(1000), MaxValueValidator(10 * 60 * 1000)]
    )
    checksum_sha256 = models.CharField(max_length=64)
    transcript = models.TextField()
    # Maps a transcript speaker label (e.g. "Leila") to that speaker's gender
    # ("female" | "male"). Regeneration assigns the female voice to "female"
    # speakers and the male voice to "male" speakers (see LISTENING_OPENAI_VOICES
    # ordering) instead of by order of first appearance, so a dialogue whose male
    # speaker talks first is not gender-reversed.
    speaker_genders = models.JSONField(null=True, blank=True, default=None)
    voice_label = models.CharField(max_length=120, blank=True)
    provenance = models.TextField()
    status = models.CharField(
        max_length=12,
        choices=MediaStatus.choices,
        default=MediaStatus.PENDING,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["content_version__item__task_type__part_number"]

    def __str__(self) -> str:
        return f"Audio for {self.content_version}"


class AudioRendition(models.Model):
    """An alternative provider-generated rendition of a canonical MediaAsset.

    The canonical asset is never overwritten: each rendition is stored at its
    own deterministic private path (``listening_renditions/{provider}/{id}.wav``)
    and kept as a separate, checksummed row. A canonical asset may have at most
    one rendition per remote provider. The field constraints (byte size, duration,
    storage key length) mirror :class:`MediaAsset` so integrity checks behave the
    same way for both.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    canonical_asset = models.ForeignKey(
        MediaAsset,
        on_delete=models.CASCADE,
        related_name="renditions",
    )
    provider = models.CharField(max_length=12, choices=RenditionProvider.choices)
    storage_key = models.CharField(max_length=240, unique=True)
    mime_type = models.CharField(max_length=80)
    byte_size = models.PositiveIntegerField(validators=[MaxValueValidator(20 * 1024 * 1024)])
    duration_ms = models.PositiveIntegerField(
        validators=[MinValueValidator(1000), MaxValueValidator(10 * 60 * 1000)]
    )
    checksum_sha256 = models.CharField(max_length=64)
    model_name = models.CharField(max_length=120)
    voice_label = models.CharField(max_length=120, blank=True)
    provenance = models.TextField()
    status = models.CharField(
        max_length=12,
        choices=MediaStatus.choices,
        default=MediaStatus.PENDING,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["canonical_asset_id", "provider"]
        constraints = [
            models.UniqueConstraint(
                fields=["canonical_asset", "provider"],
                name="media_unique_rendition_asset_provider",
            )
        ]
        indexes = [
            models.Index(
                fields=["provider", "status"],
                name="media_rendition_prov_status",
            )
        ]

    def __str__(self) -> str:
        return f"{self.provider} rendition for {self.canonical_asset}"


class MediaPlaybackGrant(models.Model):
    session = models.ForeignKey(
        AssessmentSession,
        on_delete=models.CASCADE,
        related_name="media_playback_grants",
    )
    asset = models.ForeignKey(
        MediaAsset,
        on_delete=models.CASCADE,
        related_name="playback_grants",
    )
    grants_issued = models.PositiveSmallIntegerField(default=0)
    last_granted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["session", "asset"],
                name="media_unique_session_asset_grant",
            )
        ]

    def __str__(self) -> str:
        return f"{self.session_id}: {self.asset_id} ({self.grants_issued})"
