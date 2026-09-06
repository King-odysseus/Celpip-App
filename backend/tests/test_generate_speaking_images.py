"""The generate_speaking_images command and its concept mapping."""
from __future__ import annotations

from io import StringIO
from unittest.mock import patch

import pytest
from django.core.management import call_command

from apps.content.speaking_scene_images import (
    SPEAKING_IMAGE_CONCEPTS,
    image_url_for,
)
from apps.content.speaking_seed_data import SPEAKING_SETS as SPEAKING_SETS_V1
from apps.content.speaking_seed_data_v2 import SPEAKING_SETS as SPEAKING_SETS_V2
from apps.content.speaking_seed_data_v3 import SPEAKING_SETS as SPEAKING_SETS_V3

pytestmark = pytest.mark.django_db

FAKE_PNG = b"\x89PNG\r\n\x1a\nfake-image-bytes"


def test_every_image_bearing_speaking_slug_resolves_to_a_concept():
    all_sets = SPEAKING_SETS_V1 + SPEAKING_SETS_V2 + SPEAKING_SETS_V3
    image_slugs = [s["slug"] for s in all_sets if "image_url" in s["stimulus"]]
    assert len(image_slugs) == 21
    for slug in image_slugs:
        assert image_url_for(slug) is not None, f"{slug} has no matching image concept"
    assert len({concept.filename for concept in SPEAKING_IMAGE_CONCEPTS}) == 15


def test_dry_run_lists_concepts_without_calling_the_provider(tmp_path):
    out = StringIO()
    call_command(
        "generate_speaking_images", "--out-dir", str(tmp_path), "--dry-run", stdout=out
    )
    output = out.getvalue()
    assert "would generate" in output
    assert "15 concept(s)" in output
    assert list(tmp_path.iterdir()) == []


def test_generates_one_png_per_concept_and_skips_existing_files(tmp_path):
    with patch(
        "apps.content.management.commands.generate_speaking_images.OpenAIProvider"
    ) as provider_cls:
        provider_cls.return_value.generate_image.return_value = FAKE_PNG
        out = StringIO()
        call_command(
            "generate_speaking_images", "--filename", "unusual-water-instrument",
            "--out-dir", str(tmp_path), stdout=out,
        )
    target = tmp_path / "unusual-water-instrument.png"
    assert target.is_file()
    assert target.read_bytes() == FAKE_PNG
    assert "generated=1 skipped=0 failed=0" in out.getvalue()

    # A second run without --force must not touch the existing file.
    with patch(
        "apps.content.management.commands.generate_speaking_images.OpenAIProvider"
    ) as provider_cls:
        provider_cls.return_value.generate_image.side_effect = AssertionError(
            "should not be called when the file already exists"
        )
        out = StringIO()
        call_command(
            "generate_speaking_images", "--filename", "unusual-water-instrument",
            "--out-dir", str(tmp_path), stdout=out,
        )
    assert "skipped=1" in out.getvalue()


def test_force_regenerates_an_existing_file(tmp_path):
    target = tmp_path / "unusual-greenhouse-tricycle.png"
    target.write_bytes(b"stale")
    with patch(
        "apps.content.management.commands.generate_speaking_images.OpenAIProvider"
    ) as provider_cls:
        provider_cls.return_value.generate_image.return_value = FAKE_PNG
        out = StringIO()
        call_command(
            "generate_speaking_images", "--filename", "unusual-greenhouse-tricycle",
            "--out-dir", str(tmp_path), "--force", stdout=out,
        )
    assert target.read_bytes() == FAKE_PNG
    assert "generated=1" in out.getvalue()
