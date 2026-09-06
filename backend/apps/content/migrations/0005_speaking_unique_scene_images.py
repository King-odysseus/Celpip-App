"""Repoint published Speaking stimulus images from 4 shared photos to 15 unique ones.

Every scene/predictions/unusual-object Speaking script used to point at one of
just 4 shared stock images (see the removed SCENE_*/UNUSUAL_* constants in
speaking_seed_data.py), so most learners saw the same picture regardless of
which scene or object the script actually described. generate_speaking_images
now produces one PNG per real scene concept (a "scene" script and its
matching "predictions" script share one concept by design); this migration
repoints already-published content at the new files.

The seed command skips slugs that already exist, so a database seeded before
this change keeps the old shared URLs in its stored, published
ContentVersion.stimulus JSON forever without this rewrite. Matching is by the
item's own slug (after stripping a practice-stage suffix, since every stage
variant of a scene shares its source's picture) rather than by the stale URL
value, since several different scripts shared the exact same old URL. Safe to
re-run and reversible (restores the 4-photo mapping).
"""

from django.db import migrations

_STAGE_SUFFIXES = ("-guided-stage", "-independent-stage", "-challenge-stage")

# filename (without extension) -> the source slugs whose stimulus.image_url
# should point at it. Mirrors apps/content/speaking_scene_images.py exactly;
# duplicated here rather than imported, per Django's data-migration
# convention of not depending on application code that can change later.
_NEW_IMAGE_BY_SLUG = {
    slug: filename
    for filename, slugs in {
        "scene-winter-recreation-centre": (
            "scene-winter-recreation-centre",
            "predictions-winter-recreation-centre",
        ),
        "scene-spring-farmers-market": (
            "scene-spring-farmers-market",
            "predictions-spring-farmers-market",
        ),
        "scene-summer-park-picnic": ("scene-summer-park-picnic", "predictions-summer-park"),
        "scene-community-skating-rink": (
            "scene-community-skating-rink",
            "predictions-skating-rink",
        ),
        "scene-harvest-market": ("scene-harvest-market", "predictions-harvest-market"),
        "scene-evening-recreation-centre": (
            "scene-evening-recreation-centre",
            "predictions-recreation-centre-evening",
        ),
        "scene-multi-generation-market": ("scene-multi-generation-market",),
        "predictions-transit-disruption": ("predictions-transit-disruption",),
        "unusual-water-instrument": ("unusual-water-instrument",),
        "unusual-greenhouse-tricycle": ("unusual-greenhouse-tricycle",),
        "unusual-plant-covered-vehicle": ("unusual-plant-covered-vehicle",),
        "unusual-oversized-park-instrument": ("unusual-oversized-park-instrument",),
        "unusual-floating-bicycle": ("unusual-floating-bicycle",),
        "unusual-water-powered-sculpture": ("unusual-water-powered-sculpture",),
        "unusual-robotic-delivery-device": ("unusual-robotic-delivery-device",),
    }.items()
    for slug in slugs
}

# The 4-photo scheme this migration replaces, for the reverse direction only.
_OLD_SHARED_URL_BY_FILENAME = {
    "scene-winter-recreation-centre": "/speaking/scene-recreation-centre.webp",
    "scene-community-skating-rink": "/speaking/scene-recreation-centre.webp",
    "scene-evening-recreation-centre": "/speaking/scene-recreation-centre.webp",
    "predictions-winter-recreation-centre": "/speaking/scene-recreation-centre.webp",
    "predictions-skating-rink": "/speaking/scene-recreation-centre.webp",
    "predictions-recreation-centre-evening": "/speaking/scene-recreation-centre.webp",
    "predictions-transit-disruption": "/speaking/scene-recreation-centre.webp",
    "scene-spring-farmers-market": "/speaking/scene-farmers-market.webp",
    "scene-summer-park-picnic": "/speaking/scene-farmers-market.webp",
    "scene-harvest-market": "/speaking/scene-farmers-market.webp",
    "scene-multi-generation-market": "/speaking/scene-farmers-market.webp",
    "predictions-spring-farmers-market": "/speaking/scene-farmers-market.webp",
    "predictions-summer-park": "/speaking/scene-farmers-market.webp",
    "predictions-harvest-market": "/speaking/scene-farmers-market.webp",
    "unusual-water-instrument": "/speaking/unusual-water-instrument.webp",
    "unusual-oversized-park-instrument": "/speaking/unusual-water-instrument.webp",
    "unusual-water-powered-sculpture": "/speaking/unusual-water-instrument.webp",
    "unusual-greenhouse-tricycle": "/speaking/unusual-greenhouse-tricycle.webp",
    "unusual-plant-covered-vehicle": "/speaking/unusual-greenhouse-tricycle.webp",
    "unusual-floating-bicycle": "/speaking/unusual-greenhouse-tricycle.webp",
    "unusual-robotic-delivery-device": "/speaking/unusual-greenhouse-tricycle.webp",
}


def _base_slug(item_slug: str) -> str:
    for suffix in _STAGE_SUFFIXES:
        if item_slug.endswith(suffix):
            return item_slug[: -len(suffix)]
    return item_slug


def _repoint(apps, url_by_filename: dict[str, str], *, to_new: bool) -> None:
    ContentVersion = apps.get_model("content", "ContentVersion")
    updated = []
    for version in ContentVersion.objects.filter(item__task_type__skill="speaking").iterator():
        stimulus = version.stimulus
        if not isinstance(stimulus, dict) or "image_url" not in stimulus:
            continue
        base_slug = _base_slug(version.item.slug)
        filename = _NEW_IMAGE_BY_SLUG.get(base_slug)
        if filename is None:
            continue
        target = f"/speaking/{filename}.png" if to_new else url_by_filename[filename]
        if stimulus.get("image_url") == target:
            continue
        version.stimulus = {**stimulus, "image_url": target}
        updated.append(version)

    if updated:
        ContentVersion.objects.bulk_update(updated, ["stimulus"], batch_size=200)


def to_unique_images(apps, schema_editor):
    _repoint(apps, {}, to_new=True)


def to_shared_images(apps, schema_editor):
    _repoint(apps, _OLD_SHARED_URL_BY_FILENAME, to_new=False)


class Migration(migrations.Migration):
    dependencies = [
        ("content", "0004_retire_mismatched_listening_fillers"),
    ]

    operations = [
        migrations.RunPython(to_unique_images, to_shared_images),
    ]
