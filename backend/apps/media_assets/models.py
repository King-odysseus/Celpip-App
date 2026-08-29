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
