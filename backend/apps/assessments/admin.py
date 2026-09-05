from django.contrib import admin

from .models import (
    AssessmentSession,
    ContentIssue,
    ObjectiveResult,
    Response,
    SessionItem,
    SpeakingRetry,
    SpeakingSubmission,
    WritingSubmission,
)


@admin.register(AssessmentSession)
class AssessmentSessionAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "mode", "state", "started_at", "deadline_at")
    list_filter = ("mode", "state")
    search_fields = ("id", "user__identifier")
    readonly_fields = ("guest_token_hash", "guest_expires_at")


admin.site.register(SessionItem)
admin.site.register(Response)
admin.site.register(ObjectiveResult)


@admin.register(ContentIssue)
class ContentIssueAdmin(admin.ModelAdmin):
    list_display = ("content_version", "issue_type", "status", "reporter", "created_at")
    list_filter = ("status", "issue_type")
    search_fields = ("content_version__item__title", "detail", "reporter__identifier")
    readonly_fields = ("session_item", "content_version", "reporter", "issue_type", "detail", "created_at")


@admin.register(SpeakingRetry)
class SpeakingRetryAdmin(admin.ModelAdmin):
    list_display = ("source", "retry", "created_at")
    search_fields = ("source__id", "retry__id")
    readonly_fields = ("created_at",)


@admin.register(WritingSubmission)
class WritingSubmissionAdmin(admin.ModelAdmin):
    list_display = ("session_item", "word_count", "revision", "submitted_at")
    readonly_fields = ("last_idempotency_key", "last_payload_hash")


@admin.register(SpeakingSubmission)
class SpeakingSubmissionAdmin(admin.ModelAdmin):
    list_display = (
        "session_item",
        "container",
        "byte_size",
        "duration_ms",
        "revision",
        "submitted_at",
    )
    readonly_fields = ("audio", "last_idempotency_key", "last_payload_hash")
