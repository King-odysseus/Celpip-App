from django.urls import path

from .views import AudioAccessView, AudioStreamView

app_name = "media_assets"

urlpatterns = [
    path(
        "sessions/<uuid:session_id>/media/<uuid:asset_id>/access/",
        AudioAccessView.as_view(),
        name="audio-access",
    ),
    path(
        "media/audio/<uuid:asset_id>/stream/",
        AudioStreamView.as_view(),
        name="audio-stream",
    ),
]
