from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("learning", "0002_studyplan_name"),
    ]

    operations = [
        migrations.AddField(
            model_name="studyplan",
            name="difficulty_preference",
            field=models.CharField(
                choices=[
                    ("adaptive", "Adaptive"),
                    ("foundation", "Foundation"),
                    ("developing", "Developing"),
                    ("challenge", "Challenge"),
                ],
                default="adaptive",
                max_length=16,
            ),
        ),
    ]
