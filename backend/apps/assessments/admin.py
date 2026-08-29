from django.contrib import admin

from .models import AssessmentSession, ObjectiveResult, Response, SessionItem


@admin.register(AssessmentSession)
class AssessmentSessionAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "mode", "state", "started_at", "deadline_at")
    list_filter = ("mode", "state")
    search_fields = ("id", "user__identifier")
    readonly_fields = ("guest_token_hash", "guest_expires_at")


admin.site.register(SessionItem)
admin.site.register(Response)
admin.site.register(ObjectiveResult)
