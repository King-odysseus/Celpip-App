from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("assessments", "0006_assessmentsession_assessments_session_attempt_in_range_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ContentIssue",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("issue_type", models.CharField(choices=[("audio_mismatch", "Audio does not match"), ("missing_text", "Text is incomplete"), ("ambiguous_answer", "Answer is ambiguous"), ("other", "Other")], max_length=24)),
                ("detail", models.TextField(blank=True, max_length=1000)),
                ("status", models.CharField(choices=[("open", "Open"), ("confirmed", "Confirmed — exclude from new sessions"), ("dismissed", "Dismissed")], default="open", max_length=12)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("reviewed_at", models.DateTimeField(blank=True, null=True)),
                ("content_version", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="quality_reports", to="content.contentversion")),
                ("reporter", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="content_issue_reports", to=settings.AUTH_USER_MODEL)),
                ("session_item", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="content_issues", to="assessments.sessionitem")),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.AddIndex(
            model_name="contentissue",
            index=models.Index(fields=["content_version", "status"], name="assessments_content_6d8e9b_idx"),
        ),
        migrations.AlterField(
            model_name="assessmentsession",
            name="mode",
            field=models.CharField(choices=[("learn", "Learn"), ("practice", "Practice"), ("mock", "Mock"), ("diagnostic", "Diagnostic")], max_length=12),
        ),
    ]
