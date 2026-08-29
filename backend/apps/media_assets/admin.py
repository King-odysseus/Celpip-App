from django.contrib import admin

from .models import MediaAsset, MediaPlaybackGrant


@admin.register(MediaAsset)
class MediaAssetAdmin(admin.ModelAdmin):
    list_display = ("content_version", "status", "mime_type", "duration_ms", "voice_label")
    list_filter = ("status", "mime_type")
    search_fields = ("content_version__item__title", "storage_key", "transcript")


admin.site.register(MediaPlaybackGrant)
