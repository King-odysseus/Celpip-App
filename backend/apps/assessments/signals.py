"""Storage cleanup that also runs when a parent object is cascade-deleted."""

import logging

from django.db.models.signals import post_delete
from django.dispatch import receiver

from .models import SpeakingSubmission
from .storage import private_recording_storage

logger = logging.getLogger(__name__)


@receiver(post_delete, sender=SpeakingSubmission)
def delete_speaking_audio(sender, instance: SpeakingSubmission, **kwargs) -> None:
    del sender, kwargs
    if instance.audio.name:
        # Tolerate a missing file: analyzed attempts already had their audio
        # discarded, and a cascade delete here should not fail on that.
        try:
            private_recording_storage.delete(instance.audio.name)
        except FileNotFoundError:
            logger.warning("Speaking audio already missing: %s", instance.audio.name)
