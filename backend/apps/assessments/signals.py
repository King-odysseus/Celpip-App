"""Storage cleanup that also runs when a parent object is cascade-deleted."""

from django.db.models.signals import post_delete
from django.dispatch import receiver

from .models import SpeakingSubmission
from .storage import private_recording_storage


@receiver(post_delete, sender=SpeakingSubmission)
def delete_speaking_audio(sender, instance: SpeakingSubmission, **kwargs) -> None:
    del sender, kwargs
    if instance.audio.name:
        private_recording_storage.delete(instance.audio.name)
