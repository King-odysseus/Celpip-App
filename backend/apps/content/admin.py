from django.contrib import admin, messages
from django.core.exceptions import ValidationError

from . import services
from .models import (
    Choice,
    ContentItem,
    ContentVersion,
    PublicationStatus,
    Question,
    TaskType,
    TestFormatVersion,
)


@admin.register(TestFormatVersion)
class TestFormatVersionAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "verified_on", "is_active")
    list_filter = ("is_active",)


@admin.register(TaskType)
class TaskTypeAdmin(admin.ModelAdmin):
    list_display = ("code", "title", "skill", "part_number", "is_active")
    list_filter = ("skill", "is_active")


class ContentVersionInline(admin.TabularInline):
    model = ContentVersion
    extra = 0
    fields = ("version", "status", "reviewer", "published_at")
    readonly_fields = ("status", "reviewer", "published_at")


@admin.register(ContentItem)
class ContentItemAdmin(admin.ModelAdmin):
    list_display = ("slug", "title", "task_type", "difficulty", "source_type")
    list_filter = ("task_type", "difficulty", "source_type")
    search_fields = ("slug", "title", "topic", "provenance")
    inlines = (ContentVersionInline,)


class QuestionInline(admin.TabularInline):
    model = Question
    extra = 0


@admin.register(ContentVersion)
class ContentVersionAdmin(admin.ModelAdmin):
    list_display = ("item", "version", "status", "reviewer", "published_at")
    list_filter = ("status", "item__task_type")
    inlines = (QuestionInline,)
    actions = ("submit_selected", "publish_selected", "retire_selected")

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.status in {PublicationStatus.PUBLISHED, PublicationStatus.RETIRED}:
            return tuple(field.name for field in obj._meta.fields)
        return ("reviewer", "reviewed_at", "published_at")

    @admin.action(description="Submit selected drafts for review")
    def submit_selected(self, request, queryset):
        self._run_action(request, queryset, services.submit_for_review)

    @admin.action(description="Publish selected reviewed versions")
    def publish_selected(self, request, queryset):
        self._run_action(
            request,
            queryset,
            lambda version: services.publish(version, reviewer=request.user),
        )

    @admin.action(description="Retire selected published versions")
    def retire_selected(self, request, queryset):
        self._run_action(request, queryset, services.retire)

    def _run_action(self, request, queryset, operation):
        changed = 0
        for version in queryset:
            try:
                operation(version)
                changed += 1
            except ValidationError as exc:
                self.message_user(request, f"{version}: {exc}", level=messages.ERROR)
        if changed:
            self.message_user(
                request,
                f"Updated {changed} content version(s).",
                level=messages.SUCCESS,
            )


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("content_version", "order", "skill_focus")
    list_filter = ("skill_focus", "content_version__item__task_type")


@admin.register(Choice)
class ChoiceAdmin(admin.ModelAdmin):
    list_display = ("question", "order", "is_correct")
    list_filter = ("is_correct",)
