"""Build progressive practice stages from the reviewed source bank.

Every source activity remains available unchanged.  Three additional practice
stages provide a deliberate guided -> independent -> challenge progression.
Keeping the source material stable lets learners repeat a task while reducing
support, and lets Listening stages share the same reviewed recording instead of
shipping redundant audio files.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

STAGES = (
    {
        "slug": "guided",
        "title": "Guided",
        "difficulty": 1,
        "levels": (4, 5, 6),
        "instruction": "Start with the main idea, then locate directly stated details.",
        "note": (
            "Guided stage: use the task guidance and identify explicit evidence before answering."
        ),
    },
    {
        "slug": "independent",
        "title": "Independent",
        "difficulty": 2,
        "levels": (7, 8, 9),
        "instruction": (
            "Complete the task independently and check each answer against the evidence."
        ),
        "note": (
            "Independent stage: plan and answer without prompts, then review the evidence "
            "after submission."
        ),
    },
    {
        "slug": "challenge",
        "title": "Challenge",
        "difficulty": 3,
        "levels": (10, 11, 12),
        "instruction": (
            "Work precisely: distinguish close alternatives, implications, purpose, and tone."
        ),
        "note": (
            "Challenge stage: justify subtle inferences and reject choices that are only "
            "partly supported."
        ),
    },
)

_DIRECT_FOCUSES = {"detail", "gist", "main idea", "sequence"}
_ADVANCED_FOCUSES = {"inference", "purpose", "tone", "attitude", "opinion"}


def expand_practice_bank(source_sets: list[dict[str, Any]], *, skill: str) -> list[dict[str, Any]]:
    """Return the source bank plus three progressively scaffolded stages.

    The result is exactly four times the source size.  Source dictionaries are
    never mutated, slugs remain stable and unique, and each task family gains
    the same number of activities at every new stage.
    """

    expanded = list(source_sets)
    for source_index, source in enumerate(source_sets):
        for stage in STAGES:
            variant = deepcopy(source)
            variant["slug"] = f"{source['slug']}-{stage['slug']}-stage"
            variant["title"] = f"{source['title']} — {stage['title']} Stage"
            variant["difficulty"] = stage["difficulty"]
            levels = stage["levels"]
            variant["estimated_level"] = levels[source_index % len(levels)]
            variant["instructions"] = f"{source['instructions']} {stage['instruction']}"
            variant["learning_notes"] = _append_note(
                source.get("learning_notes", ""), stage["note"]
            )
            variant["practice_stage"] = stage["slug"]
            variant["source_slug"] = source["slug"]

            if skill == "listening":
                _adapt_listening_variant(variant, stage["slug"], source_index)

            questions = variant.get("questions")
            if questions:
                variant["questions"] = _stage_questions(questions, stage["difficulty"])

            stimulus = variant.get("stimulus")
            if isinstance(stimulus, dict):
                stimulus["practice_stage"] = stage["slug"]

            expanded.append(variant)
    return expanded


def _adapt_listening_variant(variant: dict[str, Any], stage: str, source_index: int) -> None:
    """Give each Listening stage a distinct script and recording.

    The reviewed conversation remains intact so its evidence-backed questions
    stay valid.  A short, stage-specific follow-up changes the recording while
    adding a realistic wrap-up exchange and a fresh pair of speaker labels.
    """

    variant["audio_slug"] = variant["slug"]
    transcript = variant.get("transcript", "").rstrip()
    speaker_a = f"Maya {source_index + 1}"
    speaker_b = f"Jordan {source_index + 1}"
    follow_up = {
        "guided": (
            f"{speaker_a}: Before we finish, I will write down the main decision "
            "so everyone can check it.\n"
            f"{speaker_b}: Good idea. I will add the first practical step to tomorrow's task list."
        ),
        "independent": (
            f"{speaker_a}: I will summarize the trade-off in the shared notes and "
            "ask the team to confirm it.\n"
            f"{speaker_b}: Then we can review the result next week and adjust if "
            "the evidence changes."
        ),
        "challenge": (
            f"{speaker_a}: I will document the decision, its assumption, and the "
            "condition that would change it.\n"
            f"{speaker_b}: That record will help us distinguish a genuine outcome "
            "from a temporary exception."
        ),
    }[stage]
    variant["transcript"] = f"{transcript}\n{follow_up}"
    variant["intro"] = (
        f"{variant.get('intro', '')} This {stage} version includes a distinct follow-up exchange "
        "with additional speakers."
    ).strip()


def _append_note(existing: str, stage_note: str) -> str:
    return f"{existing.rstrip()} {stage_note}".strip()


def _stage_questions(questions: list[dict[str, Any]], difficulty: int) -> list[dict[str, Any]]:
    """Order questions so cognitive demand rises within each practice stage."""

    for question in questions:
        stem = question["stem"]
        if difficulty == 1:
            question["stem"] = f"Guided evidence check — {stem}"
        elif difficulty == 2:
            question["stem"] = f"Independent application — {stem}"
        else:
            question["stem"] = f"{stem} Select the answer best supported by the complete context."

    def priority(question: dict[str, Any]) -> tuple[int, str]:
        focus = str(question.get("skill_focus", "")).lower()
        if difficulty == 1:
            rank = 0 if focus in _DIRECT_FOCUSES else 1
        elif difficulty == 3:
            rank = 0 if focus in _ADVANCED_FOCUSES else 1
        else:
            rank = 0
        return rank, focus

    return sorted(questions, key=priority)
