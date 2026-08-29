"""Privacy-safe account export: ownership, coverage, and secret exclusion."""
import datetime as dt
import json

import pytest
from django.utils import timezone

from apps.accounts.models import LearnerProfile, RecoveryCode, User
from apps.assessments.models import (
    AssessmentSession,
    ObjectiveResult,
    Response,
    SessionItem,
    SpeakingSubmission,
    WritingSubmission,
)
from apps.content.models import (
    Choice,
    ContentItem,
    ContentVersion,
    PublicationStatus,
    Question,
    Skill,
    TaskType,
)
from apps.content.models import (
    TestFormatVersion as FormatVersion,
)
from apps.learning.models import MistakeRecord, StudyPlan
from apps.mocks.models import MockAttempt, MockTask

pytestmark = pytest.mark.django_db

EXPORT_URL = "/api/v1/me/export/"


def _task_type(code="reading_correspondence"):
    return TaskType.objects.create(
        code=code,
        skill=Skill.READING,
        title="Correspondence",
        part_number=1,
        description="",
        strategy=[],
        common_mistakes=[],
    )


def _content(task_type, slug="export-item"):
    item = ContentItem.objects.create(
        slug=slug,
        task_type=task_type,
        title="Export item",
        topic="A topic",
        difficulty=1,
        estimated_level=6,
        provenance="test",
    )
    version = ContentVersion.objects.create(
        item=item,
        version=1,
        status=PublicationStatus.DRAFT,
        instructions="Read the message.",
        stimulus={"body": "Hello"},
    )
    question = Question.objects.create(
        content_version=version,
        order=1,
        stem="What was said?",
        skill_focus="gist",
        evidence="secret evidence",
        explanation="secret explanation",
    )
    Choice.objects.create(question=question, order=1, text="Yes", is_correct=True)
    Choice.objects.create(question=question, order=2, text="No", is_correct=False)
    return version, question


def _submitted_session(user, version, question):
    snapshot = {
        "slug": version.item.slug,
        "title": version.item.title,
        "topic": version.item.topic,
        "task_type": version.item.task_type_id,
        "skill": version.item.task_type.skill,
        "instructions": version.instructions,
        "stimulus": version.stimulus,
        "questions": [
            {
                "id": question.id,
                "order": 1,
                "stem": question.stem,
                "skill_focus": question.skill_focus,
                "evidence": question.evidence,
                "explanation": question.explanation,
                "choices": [
                    {"id": c.id, "text": c.text, "is_correct": c.is_correct}
                    for c in question.choices.all()
                ],
            }
        ],
    }
    session = AssessmentSession.objects.create(
        user=user, mode="practice", state="submitted", submitted_at=timezone.now()
    )
    item = SessionItem.objects.create(
        session=session, content_version=version, order=1, snapshot=snapshot
    )
    wrong = question.choices.get(text="No")
    Response.objects.create(
        session_item=item, question=question, selected_choice=wrong, revision=1
    )
    ObjectiveResult.objects.create(
        session=session,
        raw_correct=0,
        raw_possible=1,
        outcomes=[
            {
                "question_id": question.id,
                "selected_choice_id": wrong.id,
                "correct_choice_id": question.choices.get(text="Yes").id,
                "is_correct": False,
                "evidence": question.evidence,
                "explanation": question.explanation,
                "choice_explanations": {str(wrong.id): "wrong explanation"},
            }
        ],
    )
    return session, item


def test_export_requires_authentication(api_client):
    assert api_client.get(EXPORT_URL).status_code == 401


def test_export_is_scoped_to_the_owner(api_client):
    task_type = _task_type()
    version, question = _content(task_type)

    owner = User.objects.create_user(identifier="owner", password="secret1")
    other = User.objects.create_user(identifier="other", password="secret1")
    LearnerProfile.objects.create(user=owner)
    LearnerProfile.objects.create(user=other)

    owner_session, _ = _submitted_session(owner, version, question)
    other_session, _ = _submitted_session(other, version, question)

    api_client.force_authenticate(owner)
    body = api_client.get(EXPORT_URL).json()
    session_ids = {s["id"] for s in body["sessions"]}
    assert str(owner_session.id) in session_ids
    assert str(other_session.id) not in session_ids


def test_export_contains_all_expected_sections(api_client):
    task_type = _task_type()
    version, question = _content(task_type)
    user = User.objects.create_user(identifier="learner", password="secret1")
    LearnerProfile.objects.create(user=user, target_level=8, exam_date=dt.date(2026, 10, 10))
    RecoveryCode.objects.create(
        user=user, code_hash=RecoveryCode.hash_code("one-time-code")
    )

    session, item = _submitted_session(user, version, question)
    WritingSubmission.objects.create(
        session_item=item, text="My authored writing.", word_count=3, revision=1
    )
    SpeakingSubmission.objects.create(
        session_item=item,
        audio="speaking/export-metadata.webm",
        mime_type="audio/webm",
        container="webm",
        byte_size=42,
        duration_ms=1000,
        revision=1,
    )
    MistakeRecord.objects.create(
        user=user,
        question=question,
        skill=Skill.READING,
        task_type=task_type,
        stem_snapshot="stem",
        selected_snapshot="No",
        correct_snapshot="Yes",
        explanation_snapshot="explained",
        first_seen_at=timezone.now(),
        last_seen_at=timezone.now(),
    )
    StudyPlan.objects.create(user=user, version=1, is_active=True, reason_summary={})
    format_version = FormatVersion.objects.create(
        code="mock-format", name="Mock", is_active=True, verified_on=dt.date(2026, 8, 29)
    )
    attempt = MockAttempt.objects.create(
        user=user, format_version=format_version, format_snapshot={"code": "mock-1"}
    )

    api_client.force_authenticate(user)
    body = api_client.get(EXPORT_URL).json()

    assert body["format_version"]
    assert body["exported_at"]
    assert body["account"]["identifier"] == "learner"
    assert body["profile"]["target_level"] == 8
    assert body["sessions"] and body["sessions"][0]["objective_result"]
    assert body["progress"]["skills"]
    assert body["mistakes"]
    assert body["study_plans"]
    assert body["mock_attempts"] and body["mock_attempts"][0]["id"] == str(attempt.id)
    # Authored response text/metadata is present.
    assert body["sessions"][0]["writing_submission"]["text"] == "My authored writing."
    assert body["sessions"][0]["speaking_submission"]["duration_ms"] == 1000
    # The session id ties back to the created session.
    assert body["sessions"][0]["id"] == str(session.id)


def _assert_no_forbidden_keys(value, forbidden, path="root"):
    """Recursively assert that answer-key/private keys never appear anywhere.

    Operates on the *structure* of the export (dict keys), not on string
    values, so legitimate prose such as the public mock disclaimer mentioning
    "objective questions" cannot cause a false positive.
    """
    if isinstance(value, dict):
        for key, child in value.items():
            assert key not in forbidden, f"forbidden key {key!r} at {path}"
            _assert_no_forbidden_keys(child, forbidden, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _assert_no_forbidden_keys(child, forbidden, f"{path}[{index}]")


def test_export_never_leaks_secrets_or_answer_keys(api_client):
    task_type = _task_type()
    version, question = _content(task_type)
    user = User.objects.create_user(identifier="learner", password="secret-password")
    LearnerProfile.objects.create(user=user)
    recovery = RecoveryCode.objects.create(
        user=user, code_hash=RecoveryCode.hash_code("one-time-code")
    )
    _submitted_session(user, version, question)
    # A mistake with distinctive answer-revealing values: the correct choice and
    # its explanation must never leave the server, but the learner's own stem
    # and selected response remain.
    MistakeRecord.objects.create(
        user=user,
        question=question,
        skill=Skill.READING,
        task_type=task_type,
        stem_snapshot="STEM-SNAPSHOT-MARKER",
        selected_snapshot="SELECTED-SNAPSHOT-MARKER",
        correct_snapshot="CORRECT-SNAPSHOT-MARKER",
        explanation_snapshot="EXPLANATION-SNAPSHOT-MARKER",
        first_seen_at=timezone.now(),
        last_seen_at=timezone.now(),
    )

    api_client.force_authenticate(user)
    body = api_client.get(EXPORT_URL).json()
    serialized = json.dumps(body)

    # Secret hashes/tokens are never present.
    assert user.password not in serialized
    assert recovery.code_hash not in serialized
    assert "one-time-code" not in serialized
    assert "guest_token_hash" not in serialized
    assert "last_idempotency_key" not in serialized
    assert "last_payload_hash" not in serialized

    # Answer keys are stripped from objective outcomes and never exported.
    assert "correct_choice_id" not in serialized
    assert "choice_explanations" not in serialized
    # The frozen question bank (with is_correct on choices) is not exported.
    session = body["sessions"][0]
    assert "questions" not in session["content"]
    outcome = session["objective_result"]["outcomes"][0]
    assert outcome == {
        "question_id": question.id,
        "selected_choice_id": question.choices.get(text="No").id,
        "is_correct": False,
    }

    # Mistake export omits the answer and its rationale, keeps the learner's data.
    assert "CORRECT-SNAPSHOT-MARKER" not in serialized
    assert "EXPLANATION-SNAPSHOT-MARKER" not in serialized
    assert "SELECTED-SNAPSHOT-MARKER" in serialized
    assert "STEM-SNAPSHOT-MARKER" in serialized


def test_export_mock_attempts_omit_snapshots_and_private_paths(api_client):
    task_type = _task_type()
    version, _question = _content(task_type)
    user = User.objects.create_user(identifier="learner", password="secret1")
    LearnerProfile.objects.create(user=user)

    format_version = FormatVersion.objects.create(
        code="export-mock-format",
        name="Mock",
        is_active=True,
        verified_on=dt.date(2026, 8, 29),
    )
    attempt = MockAttempt.objects.create(
        user=user,
        format_version=format_version,
        format_snapshot={
            "code": "export-mock-format",
            "scope": "compact_task_family_mock",
            "limitation": "practice only",
        },
    )
    session = AssessmentSession.objects.create(user=user, mode="practice")
    SessionItem.objects.create(
        session=session,
        content_version=version,
        order=1,
        snapshot={"skill": "reading", "title": "Export mock title"},
    )
    MockTask.objects.create(
        attempt=attempt,
        order=1,
        section=Skill.READING,
        task_type="reading_correspondence",
        content_version=version,
        session=session,
        snapshot={
            "title": "Export mock title",
            "questions": [
                {
                    "stem": "Q",
                    "evidence": "PRIVATE-EVIDENCE-MARKER",
                    "explanation": "PRIVATE-EXPLANATION-MARKER",
                    "choices": [{"text": "Yes", "is_correct": True}],
                }
            ],
            "audio_path": "speaking/private/recording.webm",
        },
    )

    api_client.force_authenticate(user)
    body = api_client.get(EXPORT_URL).json()
    serialized = json.dumps(body)

    assert body["mock_attempts"]
    mock_attempt = body["mock_attempts"][0]

    # Frozen task snapshots, answer keys, and private media paths never export.
    # These are asserted structurally (no such dict keys anywhere), not by
    # substring search: the public disclaimer legitimately mentions "objective
    # questions", so a plain `"questions" not in json` would be a false alarm.
    _assert_no_forbidden_keys(
        mock_attempt,
        {
            "questions",
            "snapshot",
            "audio_path",
            "evidence",
            "explanation",
            "is_correct",
            "correct_choice_id",
            "choice_explanations",
        },
    )
    assert "PRIVATE-EVIDENCE-MARKER" not in serialized
    assert "PRIVATE-EXPLANATION-MARKER" not in serialized
    assert "recording.webm" not in serialized
    # Summary metadata/results only: the embargoed attempt carries no results yet.
    assert mock_attempt["id"] == str(attempt.id)
    assert mock_attempt["results"] is None


def test_export_speaking_metadata_never_includes_audio(api_client):
    task_type = _task_type()
    version, question = _content(task_type)
    user = User.objects.create_user(identifier="learner", password="secret1")
    LearnerProfile.objects.create(user=user)
    _, item = _submitted_session(user, version, question)
    SpeakingSubmission.objects.create(
        session_item=item,
        audio="speaking/private/secret.webm",
        mime_type="audio/webm",
        container="webm",
        byte_size=42,
        duration_ms=1000,
    )

    api_client.force_authenticate(user)
    body = api_client.get(EXPORT_URL).json()
    speaking = body["sessions"][0]["speaking_submission"]

    assert speaking is not None
    assert "audio" not in speaking
    assert "secret.webm" not in json.dumps(body)
    assert speaking["mime_type"] == "audio/webm"
    assert speaking["duration_ms"] == 1000
