"""Source of truth for Speaking scene/prediction/unusual-object illustrations.

Historically every one of the 21 image-based Speaking scripts pointed at one
of just 4 shared stock photos, so most learners saw the same picture no
matter which scene or object the prompt actually described. This module
groups those 21 scripts into their real underlying *scenes* — a "scene"
script and its matching "predictions" script describe the same picture by
design (compare their ``scenario`` text), so they share one concept and one
generated image; every "unusual object" script is already standalone.

``generate_speaking_images`` (a management command) reads this list to know
what to generate and where to save it; the Speaking seed data files call
``image_url_for(slug)`` so every member of a concept resolves to the same
URL. A database already seeded before this module existed needs its stored
``ContentVersion.stimulus.image_url`` rewritten too — see the
``0005_speaking_unique_scene_images`` migration, which embeds its own copy of
this mapping rather than importing it, per Django's data-migration convention
of not depending on application code that can change later.
"""
from __future__ import annotations

from typing import NamedTuple


class SceneImageConcept(NamedTuple):
    filename: str  # relative to frontend/public/speaking/, without extension
    prompt: str
    member_slugs: tuple[str, ...]  # ContentItem slugs (pre-stage-expansion) that use this image


_SCENE_STYLE = (
    "Candid photojournalistic wide shot, natural lighting, several distinct "
    "groups of people at different distances so a viewer can describe "
    "foreground and background separately. No visible text, signage, logos, "
    "or brand names anywhere in the frame."
)
_UNUSUAL_STYLE = (
    "Whimsical, slightly surreal, well-lit photograph. The unusual object or "
    "device is the single clear main subject, centred in frame, with one or "
    "two bystanders nearby showing visible surprise or curiosity so a speaker "
    "can describe their reaction. Plain, uncluttered background. No visible "
    "text or logos."
)

SPEAKING_IMAGE_CONCEPTS: list[SceneImageConcept] = [
    SceneImageConcept(
        filename="scene-winter-recreation-centre",
        prompt=(
            "A busy indoor recreation-centre lobby on a winter afternoon in Canada. "
            "Families and children in winter coats check in at a front desk, others "
            "gather near a bulletin board, and someone laces up skates on a bench. "
            "Natural light from tall windows, warm indoor lighting. " + _SCENE_STYLE
        ),
        member_slugs=("scene-winter-recreation-centre", "predictions-winter-recreation-centre"),
    ),
    SceneImageConcept(
        filename="scene-spring-farmers-market",
        prompt=(
            "A covered outdoor farmers' market in spring, just before a light rain "
            "begins. Vendors under canvas awnings arrange fresh produce and flowers, "
            "shoppers with tote bags browse the stalls, and a few people glance up "
            "at the darkening sky. Natural daylight. " + _SCENE_STYLE
        ),
        member_slugs=("scene-spring-farmers-market", "predictions-spring-farmers-market"),
    ),
    SceneImageConcept(
        filename="scene-summer-park-picnic",
        prompt=(
            "A busy public park on a sunny summer afternoon. Several families have "
            "picnics on blankets, children play on a nearby playground, and someone "
            "grills at a picnic area. Bright natural sunlight. " + _SCENE_STYLE
        ),
        member_slugs=("scene-summer-park-picnic", "predictions-summer-park"),
    ),
    SceneImageConcept(
        filename="scene-community-skating-rink",
        prompt=(
            "An indoor community ice rink with skaters of many ages gliding on the "
            "ice, a few beginners holding the rail, and spectators watching from "
            "benches along the boards. Bright arena lighting. " + _SCENE_STYLE
        ),
        member_slugs=("scene-community-skating-rink", "predictions-skating-rink"),
    ),
    SceneImageConcept(
        filename="scene-harvest-market",
        prompt=(
            "A busy covered farmers' market during autumn harvest season, with "
            "stalls of pumpkins, apples, and squash. Shoppers carry baskets, a "
            "vendor hands a bag to a customer, warm golden light. " + _SCENE_STYLE
        ),
        member_slugs=("scene-harvest-market", "predictions-harvest-market"),
    ),
    SceneImageConcept(
        filename="scene-evening-recreation-centre",
        prompt=(
            "A recreation-centre lobby in the evening, softly lit, with a small "
            "queue of people at the front desk, a group chatting near a seating "
            "area, and someone checking a schedule board. Warm indoor lighting. "
            + _SCENE_STYLE
        ),
        member_slugs=("scene-evening-recreation-centre", "predictions-recreation-centre-evening"),
    ),
    SceneImageConcept(
        filename="scene-multi-generation-market",
        prompt=(
            "A vibrant outdoor market where grandparents, parents, and children "
            "shop together across several generations. Vendors sell fresh produce "
            "and baked goods, an older couple samples fruit, children run between "
            "stalls. Natural daylight. " + _SCENE_STYLE
        ),
        member_slugs=("scene-multi-generation-market",),
    ),
    SceneImageConcept(
        filename="predictions-transit-disruption",
        prompt=(
            "A busy urban transit platform where a delay has just been announced. "
            "Commuters check their phones, a small crowd gathers near an "
            "information screen, one person taps a foot impatiently looking down "
            "the tracks. Indoor station lighting; no readable text on any screen "
            "or sign. " + _SCENE_STYLE
        ),
        member_slugs=("predictions-transit-disruption",),
    ),
    SceneImageConcept(
        filename="unusual-water-instrument",
        prompt=(
            "An unusual homemade musical instrument built from clear tubes of "
            "water at different heights, mounted on a wooden frame in a park, "
            "played by tapping the tubes with mallets. " + _UNUSUAL_STYLE
        ),
        member_slugs=("unusual-water-instrument",),
    ),
    SceneImageConcept(
        filename="unusual-greenhouse-tricycle",
        prompt=(
            "An unusual tricycle with a small greenhouse built onto its back "
            "platform, full of potted plants and herbs, parked on a city "
            "sidewalk. " + _UNUSUAL_STYLE
        ),
        member_slugs=("unusual-greenhouse-tricycle",),
    ),
    SceneImageConcept(
        filename="unusual-plant-covered-vehicle",
        prompt=(
            "An unusual small delivery vehicle almost entirely covered in "
            "living moss and trailing plants, stopped outside a building, "
            "looking like a moving garden. " + _UNUSUAL_STYLE
        ),
        member_slugs=("unusual-plant-covered-vehicle",),
    ),
    SceneImageConcept(
        filename="unusual-oversized-park-instrument",
        prompt=(
            "An unusually oversized xylophone built from large wooden logs "
            "installed as public art in a park, taller than a person, with big "
            "mallets resting nearby. " + _UNUSUAL_STYLE
        ),
        member_slugs=("unusual-oversized-park-instrument",),
    ),
    SceneImageConcept(
        filename="unusual-floating-bicycle",
        prompt=(
            "An unusual bicycle art installation outside a gallery, suspended "
            "in mid-air above the sidewalk with no visible support, as if "
            "floating. " + _UNUSUAL_STYLE
        ),
        member_slugs=("unusual-floating-bicycle",),
    ),
    SceneImageConcept(
        filename="unusual-water-powered-sculpture",
        prompt=(
            "An unusual kinetic sculpture in a public plaza made of spinning "
            "metal wheels powered by a small stream of flowing water, catching "
            "the afternoon light. " + _UNUSUAL_STYLE
        ),
        member_slugs=("unusual-water-powered-sculpture",),
    ),
    SceneImageConcept(
        filename="unusual-robotic-delivery-device",
        prompt=(
            "An unusual small robotic delivery device shaped like a rolling "
            "cooler with tiny wheels and a sensor 'face', stopped outside a "
            "busy store. " + _UNUSUAL_STYLE
        ),
        member_slugs=("unusual-robotic-delivery-device",),
    ),
]

# Every member slug across every concept must be unique — each Speaking script
# describes exactly one picture.
_all_members = [slug for concept in SPEAKING_IMAGE_CONCEPTS for slug in concept.member_slugs]
assert len(_all_members) == len(set(_all_members)), (
    "A slug is assigned to more than one image concept."
)


def image_url_for(slug: str) -> str | None:
    """The ``/speaking/<file>.png`` URL for a source slug, or ``None`` if unmapped."""
    for concept in SPEAKING_IMAGE_CONCEPTS:
        if slug in concept.member_slugs:
            return f"/speaking/{concept.filename}.png"
    return None
