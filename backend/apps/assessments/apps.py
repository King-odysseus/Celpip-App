from django.apps import AppConfig


class AssessmentsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.assessments"

    def ready(self) -> None:
        from . import signals  # noqa: F401
