from django.contrib import admin, messages
from django.core.exceptions import ValidationError

from .models import AIFeedback, AIJob
from .services import materialize_content_draft


@admin.register(AIJob)
class AIJobAdmin(admin.ModelAdmin):
    list_display = ("id", "kind", "status", "provider", "model", "attempts", "created_at")
    list_filter = ("kind", "status", "provider")
    readonly_fields = tuple(field.name for field in AIJob._meta.fields)
    actions = ("materialize_selected",)

    @admin.action(description="Create human-review content drafts from selected jobs")
    def materialize_selected(self, request, queryset):
        created = 0
        for job in queryset:
            try:
                version, issues = materialize_content_draft(job)
            except ValidationError as exc:
                self.message_user(request, f"{job}: {exc}", level=messages.ERROR)
                continue
            created += 1
            if issues:
                self.message_user(
                    request,
                    f"{version} was saved as draft with {len(issues)} validation issue(s).",
                    level=messages.WARNING,
                )
        if created:
            self.message_user(request, f"Materialized {created} draft(s).", messages.SUCCESS)


@admin.register(AIFeedback)
class AIFeedbackAdmin(admin.ModelAdmin):
    list_display = ("session_item", "kind", "provider", "model", "created_at")
    readonly_fields = tuple(field.name for field in AIFeedback._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
