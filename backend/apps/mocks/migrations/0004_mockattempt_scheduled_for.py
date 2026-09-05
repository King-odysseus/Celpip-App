# Generated manually to keep the learner-selected simulation date explicit.

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("mocks", "0003_mockattempt_section_log")]

    operations = [
        migrations.AddField(
            model_name="mockattempt",
            name="scheduled_for",
            field=models.DateField(blank=True, help_text="Learner-selected local date for a full simulation, if scheduled.", null=True),
        ),
    ]
