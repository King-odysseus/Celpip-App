# Backfill speaker_genders for the reviewed seed dialogues so regeneration can
# assign the female/male voices by gender instead of order of first appearance.
# New seeds write this field themselves (seed_listening_content), so this only
# repairs rows created before the field existed.

from django.db import migrations

_GENDERS_BY_SLUG = {
    "apartment-heating-plan": {"Nadia": "female", "Colin": "male"},
    "pottery-class-change": {"Evan": "male", "Leila": "female"},
    "regional-transit-pass-discussion": {
        "Marisol": "female",
        "Graham": "male",
        "Sophie": "female",
    },
}


def backfill(apps, schema_editor):
    MediaAsset = apps.get_model("media_assets", "MediaAsset")
    for slug, genders in _GENDERS_BY_SLUG.items():
        MediaAsset.objects.filter(content_version__item__slug=slug).update(
            speaker_genders=genders
        )


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("media_assets", "0003_mediaasset_speaker_genders"),
    ]

    operations = [
        migrations.RunPython(backfill, noop),
    ]
