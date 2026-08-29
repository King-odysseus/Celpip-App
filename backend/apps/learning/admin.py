from django.contrib import admin

from .models import MistakeRecord, StudyPlan, StudyTask


@admin.register(MistakeRecord)
class MistakeRecordAdmin(admin.ModelAdmin):
    list_display = ("user", "skill", "task_type", "occurrences", "state", "last_seen_at")
    list_filter = ("skill", "state", "task_type")
    search_fields = ("user__identifier", "stem_snapshot")


class StudyTaskInline(admin.TabularInline):
    model = StudyTask
    extra = 0
    readonly_fields = tuple(field.name for field in StudyTask._meta.fields)


@admin.register(StudyPlan)
class StudyPlanAdmin(admin.ModelAdmin):
    list_display = ("user", "version", "is_active", "generated_at")
    list_filter = ("is_active",)
    inlines = (StudyTaskInline,)


@admin.register(StudyTask)
class StudyTaskAdmin(admin.ModelAdmin):
    list_display = ("plan", "scheduled_date", "skill", "task_type", "state")
    list_filter = ("skill", "state", "scheduled_date")
