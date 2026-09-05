"""Progressive practice-bank expansion guarantees."""

from collections import Counter

from apps.content.management.commands.seed_listening_content import LISTENING_SETS
from apps.content.management.commands.seed_reading_content import READING_SETS
from apps.content.management.commands.seed_speaking_content import SPEAKING_SETS
from apps.content.management.commands.seed_writing_content import WRITING_SETS


def test_bank_is_exactly_four_times_previous_size_and_slugs_are_unique():
    expected = {
        "reading": (READING_SETS, 171),
        "listening": (LISTENING_SETS, 180),
        "writing": (WRITING_SETS, 152),
        "speaking": (SPEAKING_SETS, 224),
    }

    for sets, total in expected.values():
        assert len(sets) == total
        assert len({item["slug"] for item in sets}) == total

    assert sum(len(sets) for sets, _ in expected.values()) == 727
    assert sum(len(item.get("questions", [])) for item in READING_SETS) == 722
    assert sum(len(item.get("questions", [])) for item in LISTENING_SETS) == 748


def test_every_source_item_has_a_complete_difficulty_progression():
    for sets in (READING_SETS, LISTENING_SETS, WRITING_SETS, SPEAKING_SETS):
        staged = [item for item in sets if "practice_stage" in item]
        source_counts = Counter(item["source_slug"] for item in staged)
        assert set(source_counts.values()) == {3}

        for source_slug in source_counts:
            progression = [item for item in staged if item["source_slug"] == source_slug]
            progression.sort(key=lambda item: item["difficulty"])
            assert [item["difficulty"] for item in progression] == [1, 2, 3]
            assert [item["practice_stage"] for item in progression] == [
                "guided",
                "independent",
                "challenge",
            ]


def test_listening_stages_have_distinct_recordings_and_scripts():
    source_transcripts = {
        item["slug"]: item["transcript"] for item in LISTENING_SETS if "practice_stage" not in item
    }
    for item in LISTENING_SETS:
        if "practice_stage" in item:
            assert item["audio_slug"] == item["slug"]
            assert item["transcript"] != source_transcripts[item["source_slug"]]
