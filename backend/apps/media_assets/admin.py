from django.contrib import admin

from .models import AudioRendition, MediaAsset, MediaPlaybackGrant


@admin.register(MediaAsset)
class MediaAssetAdmin(admin.ModelAdmin):
    list_display = ("content_version", "status", "mime_type", "duration_ms", "voice_label")
    list_filter = ("status", "mime_type")
    search_fields = ("content_version__item__title", "storage_key", "transcript")


@admin.register(AudioRendition)
class AudioRenditionAdmin(admin.ModelAdmin):
    list_display = (
        "canonical_asset",
        "provider",
        "status",
        "mime_type",
        "duration_ms",
        "model_name",
    )
    list_filter = ("provider", "status", "mime_type")
    search_fields = ("canonical_asset__storage_key", "storage_key", "model_name", "voice_label")


admin.site.register(MediaPlaybackGrant)
