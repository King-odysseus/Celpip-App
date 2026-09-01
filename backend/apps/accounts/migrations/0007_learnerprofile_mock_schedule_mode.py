from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("accounts", "0006_learnerprofile_mock_weekdays")]

    operations = [
        migrations.AddField(
            model_name="learnerprofile",
            name="mock_schedule_mode",
            field=models.CharField(
                choices=[("interval", "Every X days"), ("weekdays", "Specific days")],
                default="interval",
                help_text="Whether full mocks are scheduled by interval or selected weekdays.",
                max_length=10,
            ),
        ),
    ]
