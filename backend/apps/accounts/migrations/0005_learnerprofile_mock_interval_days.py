from django.db import migrations, models
from django.core.validators import MaxValueValidator, MinValueValidator


class Migration(migrations.Migration):
    dependencies = [("accounts", "0004_learnerprofile_preferred_audio_provider")]

    operations = [
        migrations.AddField(
            model_name="learnerprofile",
            name="mock_interval_days",
            field=models.PositiveSmallIntegerField(
                default=7,
                help_text="Days between full mock-test checkpoints.",
                validators=[MinValueValidator(1), MaxValueValidator(30)],
            ),
        ),
    ]
