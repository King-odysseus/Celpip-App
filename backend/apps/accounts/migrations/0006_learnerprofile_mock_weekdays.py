from django.db import migrations, models


def set_default_mock_days(apps, schema_editor):
    LearnerProfile = apps.get_model("accounts", "LearnerProfile")
    LearnerProfile.objects.filter(mock_weekdays__isnull=True).update(mock_weekdays=[6, 7])


class Migration(migrations.Migration):
    dependencies = [("accounts", "0005_learnerprofile_mock_interval_days")]

    operations = [
        migrations.AddField(
            model_name="learnerprofile",
            name="mock_weekdays",
            field=models.JSONField(
                default=[6, 7],
                help_text="ISO weekday numbers (Mon=1 … Sun=7) for full mock tests.",
            ),
        ),
        migrations.RunPython(set_default_mock_days, migrations.RunPython.noop),
    ]
