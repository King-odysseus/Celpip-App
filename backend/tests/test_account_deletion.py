"""Account deletion: confirmation, ownership cascade, and private media removal."""
from pathlib import Path

import pytest
from django.conf import settings
from django.core.files.base import ContentFile
from django.utils import timezone

from apps.accounts.models import LearnerProfile, RecoveryCode, User
from apps.accounts.services import (
    ConfirmationRequired,
    InvalidCredentials,
    delete_account,
)
from apps.ai_services.models import AIFeedback, AIJob, AIJobKind, AIJobStatus
from apps.assessments.models import (
    AssessmentSession,
    ObjectiveResult,
    Response,
    SessionItem,
    SpeakingSubmission,
    WritingSubmission,
)
from apps.assessments.storage import private_recording_storage
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

ME_URL = "/api/v1/me/"


@pytest.fixture(autouse=True)
def isolated_recording_storage(tmp_path, monkeypatch):
    monkeypatch.setattr(private_recording_storage, "_location", str(tmp_path))
    private_recording_storage.__dict__.pop("base_location", None)
    private_recording_storage.__dict__.pop("location", None)
    yield tmp_path


def _task_type():
    return TaskType.objects.create(
        code="reading_correspondence",
        skill=Skill.READING,
        title="Correspondence",
        part_number=1,
        description="",
        strategy=[],
        common_mistakes=[],
    )


def _content(task_type):
    item = ContentItem.objects.create(
        slug="delete-item",
        task_type=task_type,
        title="Delete item",
        topic="Topic",
        difficulty=1,
        estimated_level=6,
        provenance="test",
    )
    version = ContentVersion.objects.create(
        item=item,
        version=1,
        status=PublicationStatus.DRAFT,
        instructions="Read.",
        stimulus={},
    )
    question = Question.objects.create(
        content_version=version, order=1, stem="Q?", skill_focus="gist",
        evidence="e", explanation="x",
    )
    Choice.objects.create(question=question, order=1, text="Yes", is_correct=True)
    Choice.objects.create(question=question, order=2, text="No", is_correct=False)
    return version, question


def _owned_data(user, task_type, version, question):
    """Create representative owned rows, including a real recording and both
    PROTECT edges (MockTask.session and AIFeedback.job)."""
    session = AssessmentSession.objects.create(
        user=user, mode="mock", state="submitted", submitted_at=timezone.now()
    )
    item = SessionItem.objects.create(
        session=session, content_version=version, order=1,
        snapshot={"skill": "writing", "slug": version.item.slug},
    )
    Response.objects.create(
        session_item=item, question=question,
        selected_choice=question.choices.get(text="No"), revision=1,
    )
    WritingSubmission.objects.create(session_item=item, text="text", word_count=1, revision=1)
    ObjectiveResult.objects.create(
        session=session, raw_correct=0, raw_possible=1, outcomes=[]
    )
    audio_name = private_recording_storage.save(
        "speaking/owned.webm", ContentFile(b"\x1aE\xdf\xa3private-audio")
    )
    speaking = SpeakingSubmission.objects.create(
        session_item=item, audio=audio_name, mime_type="audio/webm",
        container="webm", byte_size=20, duration_ms=1000,
    )
    MistakeRecord.objects.create(
        user=user, question=question, skill=Skill.READING, task_type=task_type,
        stem_snapshot="s", selected_snapshot="No", correct_snapshot="Yes",
        explanation_snapshot="x", first_seen_at=timezone.now(), last_seen_at=timezone.now(),
    )
    StudyPlan.objects.create(user=user, version=1, is_active=True, reason_summary={})

    format_version = FormatVersion.objects.create(
        code="delete-format", name="Mock", is_active=True,
        verified_on=timezone.now().date(),
    )
    attempt = MockAttempt.objects.create(
        user=user, format_version=format_version, format_snapshot={}
    )
    MockTask.objects.create(
        attempt=attempt, order=1, section=Skill.READING, task_type="reading_correspondence",
        content_version=version, session=session, snapshot={},
    )
    job = AIJob.objects.create(
        kind=AIJobKind.WRITING_FEEDBACK, status=AIJobStatus.SUCCEEDED,
        session_item=item, provider="fake", model="m", prompt_version="v",
        run_after=timezone.now(),
    )
    AIFeedback.objects.create(
        session_item=item, job=job, kind=AIJobKind.WRITING_FEEDBACK,
        provider="fake", model="m", prompt_version="v", assessment={},
    )
    return Path(speaking.audio.path)


def test_delete_requires_confirmation(api_client):
    user = User.objects.create_user(identifier="learner", password="secret1")
    api_client.force_authenticate(user)
    resp = api_client.delete(ME_URL, {}, format="json")
    assert resp.status_code == 400
    assert resp.json()["code"] == "invalid_input"
    assert User.objects.filter(pk=user.pk).exists()


def test_delete_wrong_confirmation_is_generic(api_client):
    user = User.objects.create_user(identifier="learner", password="secret1")
    api_client.force_authenticate(user)
    resp = api_client.delete(ME_URL, {"password": "wrong-one"}, format="json")
    assert resp.status_code == 400
    assert resp.json()["code"] == "invalid_credentials"
    assert User.objects.filter(pk=user.pk).exists()


def test_delete_with_password_cascades_owned_data_and_recording(api_client):
    task_type = _task_type()
    version, question = _content(task_type)
    user = User.objects.create_user(identifier="learner", password="secret1")
    LearnerProfile.objects.create(user=user)
    RecoveryCode.objects.create(user=user, code_hash=RecoveryCode.hash_code("code"))
    recording_path = _owned_data(user, task_type, version, question)
    assert recording_path.exists()

    api_client.force_authenticate(user)
    resp = api_client.delete(ME_URL, {"password": "secret1"}, format="json")

    assert resp.status_code == 204
    assert not User.objects.filter(pk=user.pk).exists()
    assert not AssessmentSession.objects.filter(user_id=user.pk).exists()
    assert not MistakeRecord.objects.filter(user_id=user.pk).exists()
    assert not StudyPlan.objects.filter(user_id=user.pk).exists()
    assert not MockAttempt.objects.filter(user_id=user.pk).exists()
    assert not SpeakingSubmission.objects.exists()
    assert not AIJob.objects.filter(session_item__session__user_id=user.pk).exists()
    assert not recording_path.exists()


def test_delete_with_recovery_code_works(api_client):
    user = User.objects.create_user(identifier="learner", password="secret1")
    RecoveryCode.objects.create(user=user, code_hash=RecoveryCode.hash_code("my-code"))
    api_client.force_authenticate(user)
    resp = api_client.delete(ME_URL, {"recovery_code": "my-code"}, format="json")
    assert resp.status_code == 204
    assert not User.objects.filter(pk=user.pk).exists()


def test_delete_clears_refresh_cookie_on_204(api_client):
    user = User.objects.create_user(identifier="learner", password="secret1")
    api_client.force_authenticate(user)
    # Simulate a browser that still holds a refresh cookie for this account.
    api_client.cookies[settings.AUTH_REFRESH_COOKIE_NAME] = "stale-refresh-token"

    resp = api_client.delete(ME_URL, {"password": "secret1"}, format="json")

    assert resp.status_code == 204
    assert not User.objects.filter(pk=user.pk).exists()
    cookie = resp.cookies[settings.AUTH_REFRESH_COOKIE_NAME]
    assert cookie.value == ""
    # Expired rather than merely absent: the cookie is cleared, not left behind.
    # Django's morsel serializes max-age as an integer 0; accept either form.
    assert int(cookie["max-age"]) == 0


def test_used_recovery_code_cannot_confirm_deletion(api_client):
    user = User.objects.create_user(identifier="learner", password="secret1")
    RecoveryCode.objects.create(
        user=user, code_hash=RecoveryCode.hash_code("spent"), used_at=timezone.now()
    )
    api_client.force_authenticate(user)
    resp = api_client.delete(ME_URL, {"recovery_code": "spent"}, format="json")
    assert resp.status_code == 400
    assert resp.json()["code"] == "invalid_credentials"
    assert User.objects.filter(pk=user.pk).exists()


def test_service_raises_confirmation_required_without_credentials():
    user = User.objects.create_user(identifier="learner", password="secret1")
    with pytest.raises(ConfirmationRequired):
        delete_account(user)
    with pytest.raises(InvalidCredentials):
        delete_account(user, password="nope")
