"""Allow several MockTasks per task_type so a section can reach the exact
official question count by combining distinct content versions (Phase 11).
Duplicate content within one attempt is still prevented, now keyed on the
content version itself rather than the task_type.
"""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("mocks", "0001_initial"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="mocktask",
            name="mocks_unique_attempt_task_type",
        ),
        migrations.AddConstraint(
            model_name="mocktask",
            constraint=models.UniqueConstraint(
                fields=("attempt", "content_version"),
                name="mocks_unique_attempt_content_version",
            ),
        ),
    ]
