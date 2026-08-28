"""Admin registration for account models.

Passwords and recovery-code hashes are never editable as plain text here.
"""
from __future__ import annotations

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import LearnerProfile, RecoveryCode, User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    ordering = ("identifier",)
    list_display = ("identifier", "email", "is_active", "is_staff", "date_joined")
    list_filter = ("is_active", "is_staff", "is_superuser")
    search_fields = ("identifier", "email")
    readonly_fields = ("date_joined", "last_login")

    fieldsets = (
        (None, {"fields": ("identifier", "password")}),
        ("Contact", {"fields": ("email",)}),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("identifier", "password1", "password2"),
            },
        ),
    )


@admin.register(LearnerProfile)
class LearnerProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "exam_date", "target_level", "daily_minutes", "timezone")
    search_fields = ("user__identifier",)
    raw_id_fields = ("user",)


@admin.register(RecoveryCode)
class RecoveryCodeAdmin(admin.ModelAdmin):
    list_display = ("user", "created_at", "used_at")
    search_fields = ("user__identifier",)
    readonly_fields = ("code_hash", "created_at", "used_at")
    raw_id_fields = ("user",)
