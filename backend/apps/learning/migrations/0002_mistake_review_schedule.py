from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("learning", "0001_initial")]

    operations = [
        migrations.AddField(
            model_name="mistakerecord",
            name="next_review_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="mistakerecord",
            name="review_interval_days",
            field=models.PositiveSmallIntegerField(default=1),
        ),
        migrations.AddField(
            model_name="mistakerecord",
            name="review_count",
            field=models.PositiveIntegerField(default=0),
        ),
    ]
