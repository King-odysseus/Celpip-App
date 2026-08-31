"""Repoint seeded Speaking stimulus images from PNG to WebP.

The seed command skips slugs that already exist, so databases seeded before
the WebP conversion keep the old ``.png`` paths in their stimulus JSON. This
rewrites them in place. It is safe to re-run and reversible.
"""

from django.db import migrations

IMAGE_STEMS = (
    "scene-recreation-centre",
    "scene-farmers-market",
    "unusual-water-instrument",
    "unusual-greenhouse-tricycle",
)


def _reencode(apps, from_ext: str, to_ext: str) -> None:
    ContentVersion = apps.get_model("content", "ContentVersion")
    renames = {
        f"/speaking/{stem}{from_ext}": f"/speaking/{stem}{to_ext}"
        for stem in IMAGE_STEMS
    }

    updated = []
    for version in ContentVersion.objects.filter(
        item__task_type__skill="speaking"
    ).iterator():
        stimulus = version.stimulus
        if not isinstance(stimulus, dict):
            continue
        target = renames.get(stimulus.get("image_url"))
        if not target:
            continue
        version.stimulus = {**stimulus, "image_url": target}
        updated.append(version)

    if updated:
        ContentVersion.objects.bulk_update(updated, ["stimulus"], batch_size=200)


def to_webp(apps, schema_editor):
    _reencode(apps, ".png", ".webp")


def to_png(apps, schema_editor):
    _reencode(apps, ".webp", ".png")


class Migration(migrations.Migration):
    dependencies = [
        ("content", "0002_testformatversion_component_order_and_more"),
    ]

    operations = [
        migrations.RunPython(to_webp, to_png),
    ]
