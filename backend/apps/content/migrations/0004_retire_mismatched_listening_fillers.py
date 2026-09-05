from django.db import migrations


FILLER_SLUGS = [
    "lost-umbrella-front-desk",
    "returning-a-library-tablet",
    "power-outage-building-notice",
    "gym-schedule-change",
    "should-parks-charge-entry-fees",
]


def retire_fillers(apps, schema_editor):
    ContentVersion = apps.get_model("content", "ContentVersion")
    ContentVersion.objects.filter(
        item__slug__in=FILLER_SLUGS,
        status="published",
    ).update(status="retired")


class Migration(migrations.Migration):
    dependencies = [("content", "0003_speaking_image_webp")]
    operations = [migrations.RunPython(retire_fillers, migrations.RunPython.noop)]
