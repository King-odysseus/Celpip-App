from django.contrib import admin

from .models import MockAttempt, MockTask


class MockTaskInline(admin.TabularInline):
    model = MockTask
    extra = 0
    readonly_fields = tuple(field.name for field in MockTask._meta.fields)


@admin.register(MockAttempt)
class MockAttemptAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "state", "current_section", "created_at")
    list_filter = ("state", "current_section", "format_version")
    inlines = (MockTaskInline,)


@admin.register(MockTask)
class MockTaskAdmin(admin.ModelAdmin):
    list_display = ("attempt", "order", "section", "task_type", "state")
    list_filter = ("section", "state", "task_type")
