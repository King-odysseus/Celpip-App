"""Full-length mock assembly, unscored exclusion, and content-protection tests.

Compact-mock behaviour is covered by test_mocks.py / test_mock_rules.py and is
untouched by Phase 11 — these tests target only ``scope=FULL_LENGTH_SCOPE``.
"""
from io import StringIO

import pytest
from django.core.management import call_command

from apps.accounts.models import User
from apps.assessments.models import SessionMode, SessionState
from apps.content.models import Skill
from apps.mocks.models import MockTask
from apps.mocks.services import (
    FULL_LENGTH_SCOPE,
    OFFICIAL_COUNTS,
    MockUnavailable,
    create_attempt,
    results_payload,
)

pytestmark = pytest.mark.django_db

OBJECTIVE_TASK_TYPES = {
    code: target
    for code, target in OFFICIAL_COUNTS.items()
    if code.startswith("listening_") or code.startswith("reading_")
}


@pytest.fixture
def full_bank():
    call_command("seed_reading_content", verbosity=0, stdout=StringIO())
    call_command("seed_writing_content", verbosity=0, stdout=StringIO())
    call_command("seed_speaking_content", verbosity=0, stdout=StringIO())
    call_command("seed_listening_content", verbosity=0, stdout=StringIO())


@pytest.fixture
def user(full_bank):
    return User.objects.create_user(identifier="full-mock-taker", password="secret1")


def _question_counts_by_task_type(attempt):
    counts: dict[str, int] = {}
    for task in attempt.tasks.select_related("content_version"):
        counts[task.task_type] = counts.get(task.task_type, 0) + task.content_version.questions.count()
    return counts


# --- Exact question counts --------------------------------------------------


def test_full_length_hits_every_official_question_count_exactly(user):
    attempt = create_attempt(user, scope=FULL_LENGTH_SCOPE)
    counts = _question_counts_by_task_type(attempt)
    for code, target in OBJECTIVE_TASK_TYPES.items():
        assert counts[code] == target, f"{code}: expected {target}, got {counts[code]}"


def test_full_length_keeps_exactly_one_writing_and_speaking_task_each(user):
    attempt = create_attempt(user, scope=FULL_LENGTH_SCOPE)
    for code in OFFICIAL_COUNTS:
        if code.startswith("writing_") or code.startswith("speaking_"):
            assert attempt.tasks.filter(task_type=code).count() == 1


# --- Complete task-family coverage -----------------------------------------


def test_full_length_covers_all_20_task_families_in_component_order(user):
    attempt = create_attempt(user, scope=FULL_LENGTH_SCOPE)
    task_types_seen = list(
        dict.fromkeys(attempt.tasks.order_by("order").values_list("task_type", flat=True))
    )
    assert sorted(task_types_seen) == sorted(OFFICIAL_COUNTS)

    sections = list(attempt.tasks.order_by("order").values_list("section", flat=True))
    # Every listening task precedes every reading task, which precedes every
    # writing task, which precedes every speaking task.
    boundaries = [sections.index(skill) for skill in (Skill.READING, Skill.WRITING, Skill.SPEAKING)]
    assert boundaries == sorted(boundaries)
    assert sections[0] == Skill.LISTENING
    assert sections[-1] == Skill.SPEAKING


# --- Variant selection and duplicate prevention -----------------------------


def test_full_length_never_duplicates_a_content_version_within_one_attempt(user):
    attempt = create_attempt(user, scope=FULL_LENGTH_SCOPE)
    version_ids = list(attempt.tasks.values_list("content_version_id", flat=True))
    assert len(version_ids) == len(set(version_ids))


def test_repeated_full_length_attempts_vary_which_content_is_selected(user):
    """Not every attempt should reuse the identical complete test.

    Some individual sections have only one exact combination available, so
    this asserts variety across the WHOLE attempt (any differing task) rather
    than requiring every section to differ every time.
    """
    first = create_attempt(user, scope=FULL_LENGTH_SCOPE)
    first_versions = set(first.tasks.values_list("content_version_id", flat=True))

    found_variation = False
    for _ in range(5):
        again = create_attempt(user, scope=FULL_LENGTH_SCOPE)
        if set(again.tasks.values_list("content_version_id", flat=True)) != first_versions:
            found_variation = True
            break
    assert found_variation, "Repeated full-length mocks always assembled the identical test."


# --- Unscored-item exclusion -------------------------------------------------


def test_unscored_items_are_flagged_and_excluded_from_raw_results(user):
    from apps.assessments.models import AssessmentSession
    from apps.assessments.services import submit_session, submit_writing
    from apps.mocks.services import advance_attempt, start_attempt

    attempt = create_attempt(user, scope=FULL_LENGTH_SCOPE)
    unscored = list(attempt.tasks.filter(is_simulated_unscored=True))
    assert unscored, "Expect at least one simulated-unscored item in a full-length mock."

    attempt, _ = start_attempt(attempt.id, user)
    total_possible_scored = 0
    total_possible_all = 0
    while attempt.state != "completed":
        task = MockTask.objects.select_related("session", "content_version").get(
            attempt=attempt, order=attempt.current_order
        )
        if task.section in (Skill.LISTENING, Skill.READING):
            question_count = task.content_version.questions.count()
            total_possible_all += question_count
            if not task.is_simulated_unscored:
                total_possible_scored += question_count
            submit_session(task.session)
        elif task.section == Skill.WRITING:
            submit_writing(task.session, final_text="A complete mock response with enough words.")
        else:
            from django.utils import timezone

            AssessmentSession.objects.filter(pk=task.session_id).update(
                state=SessionState.SUBMITTED, submitted_at=timezone.now()
            )
        attempt, _ = advance_attempt(attempt.id, user, expected_order=attempt.current_order)

    results = results_payload(attempt)
    objective = {c["skill"]: c for c in results["components"] if c["skill"] in (Skill.LISTENING, Skill.READING)}
    reported_possible = sum(c["raw_possible"] for c in objective.values())
    reported_scored_items = sum(c["items_scored"] for c in objective.values())
    reported_attempted_items = sum(c["items_attempted"] for c in objective.values())

    assert reported_possible == total_possible_scored
    assert reported_possible < total_possible_all
    assert reported_scored_items < reported_attempted_items


# --- Immutable snapshots and answer-key protection --------------------------


def test_full_length_task_snapshot_and_unscored_flag_are_immutable(user):
    attempt = create_attempt(user, scope=FULL_LENGTH_SCOPE)
    task = attempt.tasks.first()
    task.is_simulated_unscored = not task.is_simulated_unscored
    with pytest.raises(Exception):
        task.save()

    task.refresh_from_db()
    task.snapshot = {**task.snapshot, "title": "Tampered"}
    with pytest.raises(Exception):
        task.save()


def test_full_length_session_hides_correct_choice(user):
    """A frozen SessionItem snapshot still carries is_correct (server-only);
    the learner-facing API must never surface it before submission — this is
    already enforced by PublicContentSerializer/session payload for every
    mode, so this test asserts the mock's frozen content keeps that data
    intact for scoring while the API-level guarantee is covered by
    test_reading.py's existing answer-key tests. Here we confirm every
    objective task's snapshot has exactly one correct choice per question,
    so scoring can never silently short-circuit to 0/0.
    """
    attempt = create_attempt(user, scope=FULL_LENGTH_SCOPE)
    for task in attempt.tasks.filter(section__in=[Skill.LISTENING, Skill.READING]):
        for question in task.snapshot["questions"]:
            correct = [choice for choice in question["choices"] if choice["is_correct"]]
            assert len(correct) == 1


# --- Format-version behaviour ------------------------------------------------


def test_full_length_format_snapshot_declares_its_own_scope_and_limitation(user):
    attempt = create_attempt(user, scope=FULL_LENGTH_SCOPE)
    assert attempt.scope == FULL_LENGTH_SCOPE
    assert attempt.format_snapshot["scope"] == FULL_LENGTH_SCOPE
    assert "unofficial" in attempt.format_snapshot["limitation"].lower()
    assert attempt.format_snapshot["task_structure"]
    assert attempt.format_snapshot["component_order"][0] == Skill.LISTENING


# --- Raw result accuracy -----------------------------------------------------


def test_full_length_raw_accuracy_reflects_only_scored_correct_answers(user):
    from uuid import uuid4

    from apps.assessments.services import save_response, submit_session
    from apps.mocks.services import advance_attempt, start_attempt

    attempt = create_attempt(user, scope=FULL_LENGTH_SCOPE)
    attempt, _ = start_attempt(attempt.id, user)

    # Answer the very first (Listening) task's first question incorrectly on
    # purpose, then submit, to prove raw_correct reflects real answers rather
    # than always matching raw_possible.
    task = MockTask.objects.select_related("session", "content_version").get(
        attempt=attempt, order=attempt.current_order
    )
    question = task.content_version.questions.order_by("order").first()
    wrong_choice = question.choices.filter(is_correct=False).first()
    save_response(
        session=task.session,
        question_id=question.id,
        choice_id=wrong_choice.id,
        expected_revision=0,
        idempotency_key=uuid4(),
    )
    result = submit_session(task.session)
    assert result.raw_correct < result.raw_possible


# --- Unavailable-content guard ------------------------------------------------


def test_full_length_raises_when_a_task_type_cannot_reach_its_official_count(user):
    from apps.content.models import ContentItem
    from apps.media_assets.models import MediaAsset

    # Delete every published Listening Information item (and its private audio
    # metadata, which otherwise protects the content from deletion) so that
    # section can no longer reach its official 6-question target.
    items = ContentItem.objects.filter(task_type_id="listening_information")
    MediaAsset.objects.filter(content_version__item__in=items).delete()
    items.delete()
    with pytest.raises(MockUnavailable):
        create_attempt(user, scope=FULL_LENGTH_SCOPE)


def test_compact_mock_is_still_available_and_unaffected(user):
    """Phase 11 keeps the original compact scope working unchanged."""
    from apps.mocks.services import COMPACT_SCOPE

    attempt = create_attempt(user, scope=COMPACT_SCOPE)
    assert attempt.scope == COMPACT_SCOPE
    assert attempt.tasks.count() == 20
    assert attempt.tasks.filter(is_simulated_unscored=True).count() == 0


# --- Completion review: time used, unanswered items, next steps -----------


def _complete_full_length_attempt(user):
    """Drive a fresh full-length attempt to completion, answering every
    objective question correctly, and return the completed attempt."""
    from apps.assessments.models import AssessmentSession
    from apps.assessments.services import save_response, submit_session, submit_writing
    from apps.mocks.services import advance_attempt, start_attempt
    from uuid import uuid4

    attempt = create_attempt(user, scope=FULL_LENGTH_SCOPE)
    attempt, _ = start_attempt(attempt.id, user)

    while attempt.state != "completed":
        task = MockTask.objects.select_related("session", "content_version").get(
            attempt=attempt, order=attempt.current_order
        )
        if task.section in (Skill.LISTENING, Skill.READING):
            item = task.session.items.get()
            for question in item.content_version.questions.prefetch_related("choices"):
                correct_choice = next(choice for choice in question.choices.all() if choice.is_correct)
                save_response(
                    session=task.session,
                    question_id=question.id,
                    choice_id=correct_choice.id,
                    expected_revision=0,
                    idempotency_key=uuid4(),
                )
            submit_session(task.session)
        elif task.section == Skill.WRITING:
            submit_writing(task.session, final_text="A complete mock response with enough words.")
        else:
            from django.utils import timezone

            AssessmentSession.objects.filter(pk=task.session_id).update(
                state=SessionState.SUBMITTED, submitted_at=timezone.now()
            )
        attempt, _ = advance_attempt(attempt.id, user, expected_order=attempt.current_order)
    return attempt


def test_completion_review_reports_time_used_per_section(user):
    attempt = _complete_full_length_attempt(user)
    results = results_payload(attempt)

    for component in results["components"]:
        assert component["time_used_seconds"] is not None
        assert component["time_used_seconds"] >= 0
    assert results["time_used_seconds_total"] is not None
    assert results["time_used_seconds_total"] >= 0


def test_completion_review_reports_no_unanswered_tasks_when_all_submitted(user):
    attempt = _complete_full_length_attempt(user)
    results = results_payload(attempt)

    assert results["tasks_unanswered_total"] == 0
    for component in results["components"]:
        assert component["tasks_unanswered"] == 0


def test_completion_review_identifies_strongest_and_needs_attention_skills(user):
    attempt = _complete_full_length_attempt(user)
    results = results_payload(attempt)

    all_skills = {Skill.LISTENING, Skill.READING, Skill.WRITING, Skill.SPEAKING}
    assert results["strongest_skill"] in all_skills
    assert results["needs_attention_skill"] in all_skills
    # Every recommendation is honest about where it sends the learner and why.
    for step in results["recommended_next_steps"]:
        assert step["skill"] in all_skills
        assert step["reason"]
        assert step["destination"].startswith("/")


def test_completion_review_never_claims_an_overall_celpip_level(user):
    attempt = _complete_full_length_attempt(user)
    results = results_payload(attempt)

    assert results["overall_score"] is None
    assert "unofficial" in results["disclaimer"].lower()


def test_completion_review_counts_skipped_tasks_as_unanswered(user):
    """A section that expires mid-way marks its unfinished tasks skipped;
    the completion review must surface those as unanswered, and recommend
    revisiting that skill."""
    from apps.mocks.services import _expire_locked
    from django.utils import timezone

    attempt = create_attempt(user, scope=FULL_LENGTH_SCOPE)
    from apps.mocks.services import start_attempt

    attempt, _ = start_attempt(attempt.id, user)
    first_section = attempt.current_section

    # Force the first section's deadline into the past and let it expire,
    # skipping every remaining task in that section without answering them.
    attempt.section_deadline_at = timezone.now() - __import__("datetime").timedelta(seconds=1)
    attempt.save()
    _expire_locked(attempt, timezone.now())
    attempt.save()

    # Finish the remaining sections normally.
    attempt = _drain_remaining(attempt, user)

    results = results_payload(attempt)
    skipped_component = next(c for c in results["components"] if c["skill"] == first_section)
    assert skipped_component["tasks_unanswered"] > 0
    assert results["tasks_unanswered_total"] > 0
    assert any(step["skill"] == first_section for step in results["recommended_next_steps"])


def _drain_remaining(attempt, user):
    from apps.assessments.models import AssessmentSession
    from apps.assessments.services import submit_session, submit_writing
    from apps.mocks.services import advance_attempt
    from django.utils import timezone

    while attempt.state != "completed":
        task = MockTask.objects.select_related("session", "content_version").get(
            attempt=attempt, order=attempt.current_order
        )
        if task.section in (Skill.LISTENING, Skill.READING):
            submit_session(task.session)
        elif task.section == Skill.WRITING:
            submit_writing(task.session, final_text="A complete mock response with enough words.")
        else:
            AssessmentSession.objects.filter(pk=task.session_id).update(
                state=SessionState.SUBMITTED, submitted_at=timezone.now()
            )
        attempt, _ = advance_attempt(attempt.id, user, expected_order=attempt.current_order)
    return attempt
