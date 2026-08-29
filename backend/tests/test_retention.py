"""Retention command: dry-run default, execute, boundaries, and cascades."""
from datetime import timedelta
from io import StringIO
from pathlib import Path

import pytest
from django.core.files.base import ContentFile
from django.core.management import call_command
from django.core.management.base import CommandError
from django.utils import timezone

from apps.accounts.models import User
from apps.ai_services.models import AIFeedback, AIJob, AIJobKind, AIJobStatus
from apps.assessments.models import AssessmentSession, SessionItem, SpeakingSubmission
from apps.assessments.storage import private_recording_storage
from apps.content.models import (
    ContentItem,
    ContentVersion,
    PublicationStatus,
    Skill,
    TaskType,
)

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def isolated_recording_storage(tmp_path, monkeypatch):
    monkeypatch.setattr(private_recording_storage, "_location", str(tmp_path))
    private_recording_storage.__dict__.pop("base_location", None)
    private_recording_storage.__dict__.pop("location", None)
    yield tmp_path


def _version(*, code="retention_reading", slug="retention-item", part_number=1):
    task_type = TaskType.objects.create(
        code=code, skill=Skill.READING, title="t", part_number=part_number,
        description="", strategy=[], common_mistakes=[],
    )
    item = ContentItem.objects.create(
        slug=slug, task_type=task_type, title="t", topic="t",
        difficulty=1, estimated_level=5, provenance="t",
    )
    return ContentVersion.objects.create(
        item=item, version=1, status=PublicationStatus.PUBLISHED,
        instructions="", stimulus={},
    )


def _expired_guest_session(version, *, with_recording=False):
    session = AssessmentSession.objects.create(
        user=None,
        mode="practice",
        guest_token_hash="0" * 64,
        guest_expires_at=timezone.now() - timedelta(hours=48),
    )
    item = SessionItem.objects.create(
        session=session, content_version=version, order=1,
        snapshot={"skill": "speaking"},
    )
    if with_recording:
        name = private_recording_storage.save(
            "speaking/guest.webm", ContentFile(b"\x1aE\xdf\xa3guest-audio")
        )
        SpeakingSubmission.objects.create(
            session_item=item, audio=name, mime_type="audio/webm",
            container="webm", byte_size=11, duration_ms=1000,
        )
    return session, item


def _failed_job(item, *, age_days):
    return AIJob.objects.create(
        kind=AIJobKind.WRITING_FEEDBACK, status=AIJobStatus.FAILED,
        session_item=item, provider="fake", model="m", prompt_version="v",
        run_after=timezone.now() - timedelta(days=age_days),
        completed_at=timezone.now() - timedelta(days=age_days),
    )


def test_dry_run_is_default_and_deletes_nothing():
    version = _version()
    session, item = _expired_guest_session(version, with_recording=True)
    _failed_job(item, age_days=60)

    out = StringIO()
    call_command("retention", stdout=out)

    assert "[dry-run]" in out.getvalue()
    assert AssessmentSession.objects.filter(pk=session.pk).exists()
    assert AIJob.objects.filter(status=AIJobStatus.FAILED).exists()


def test_execute_deletes_expired_guest_sessions_and_recordings():
    version = _version()
    session, item = _expired_guest_session(version, with_recording=True)
    recording_path = Path(
        private_recording_storage.path(
            SpeakingSubmission.objects.get().audio.name
        )
    )
    assert recording_path.exists()

    out = StringIO()
    call_command("retention", "--execute", stdout=out)

    assert not AssessmentSession.objects.filter(pk=session.pk).exists()
    assert not SessionItem.objects.filter(session_id=session.pk).exists()
    assert not SpeakingSubmission.objects.exists()
    assert not recording_path.exists()
    assert "Deleted" in out.getvalue()


def test_execute_deletes_stale_failed_ai_jobs_with_protected_feedback():
    version = _version()
    session, item = _expired_guest_session(version)
    job = _failed_job(item, age_days=60)
    AIFeedback.objects.create(
        session_item=item, job=job, kind=AIJobKind.WRITING_FEEDBACK,
        provider="fake", model="m", prompt_version="v", assessment={},
    )

    call_command("retention", "--execute", stdout=StringIO())

    assert not AIJob.objects.filter(pk=job.pk).exists()
    assert not AIFeedback.objects.exists()


def test_execute_deletes_stale_failed_jobs_in_authenticated_sessions():
    # A stale FAILED job in an authenticated, non-expired session still needs
    # its PROTECTed feedback cleared before the job itself can be removed. The
    # authenticated session must survive.
    version = _version()
    user = User.objects.create_user(identifier="retained-user", password="secret1")
    session = AssessmentSession.objects.create(user=user, mode="practice")
    item = SessionItem.objects.create(
        session=session, content_version=version, order=1, snapshot={"skill": "writing"},
    )
    job = _failed_job(item, age_days=60)
    AIFeedback.objects.create(
        session_item=item, job=job, kind=AIJobKind.WRITING_FEEDBACK,
        provider="fake", model="m", prompt_version="v", assessment={},
    )

    call_command("retention", "--execute", stdout=StringIO())

    assert not AIJob.objects.filter(pk=job.pk).exists()
    assert not AIFeedback.objects.exists()
    assert AssessmentSession.objects.filter(pk=session.pk).exists()
    assert SessionItem.objects.filter(pk=item.pk).exists()


def test_execute_preserves_successful_running_and_fresh_jobs():
    user = User.objects.create_user(identifier="retained-user", password="secret1")
    session = AssessmentSession.objects.create(user=user, mode="practice")

    def _item(order, version):
        return SessionItem.objects.create(
            session=session, content_version=version, order=order,
            snapshot={"skill": "writing"},
        )

    # A successful job + its feedback must survive.
    success_item = _item(1, _version(part_number=1, slug="retention-item"))
    success_job = AIJob.objects.create(
        kind=AIJobKind.WRITING_FEEDBACK, status=AIJobStatus.SUCCEEDED,
        session_item=success_item, provider="fake", model="m", prompt_version="v",
        run_after=timezone.now() - timedelta(days=60),
        completed_at=timezone.now() - timedelta(days=60),
    )
    AIFeedback.objects.create(
        session_item=success_item, job=success_job, kind=AIJobKind.WRITING_FEEDBACK,
        provider="fake", model="m", prompt_version="v", assessment={},
    )

    # A running job must survive.
    running_item = _item(
        2, _version(code="retention_reading_2", slug="retention-item-2", part_number=2)
    )
    running_job = AIJob.objects.create(
        kind=AIJobKind.WRITING_FEEDBACK, status=AIJobStatus.RUNNING,
        session_item=running_item, provider="fake", model="m", prompt_version="v",
        run_after=timezone.now() - timedelta(days=60),
        completed_at=timezone.now() - timedelta(days=60),
    )

    # A fresh (non-stale) failed job must survive.
    fresh_item = _item(
        3, _version(code="retention_reading_3", slug="retention-item-3", part_number=3)
    )
    fresh_job = AIJob.objects.create(
        kind=AIJobKind.WRITING_FEEDBACK, status=AIJobStatus.FAILED,
        session_item=fresh_item, provider="fake", model="m", prompt_version="v",
        run_after=timezone.now(), completed_at=timezone.now(),
    )

    call_command("retention", "--execute", stdout=StringIO())

    assert AIJob.objects.filter(pk=success_job.pk).exists()
    assert AIFeedback.objects.filter(job_id=success_job.pk).exists()
    assert AIJob.objects.filter(pk=running_job.pk).exists()
    assert AIJob.objects.filter(pk=fresh_job.pk).exists()
    assert AssessmentSession.objects.filter(pk=session.pk).exists()


def test_fresh_guest_sessions_and_jobs_are_untouched():
    version = _version()
    session = AssessmentSession.objects.create(
        user=None, mode="practice",
        guest_token_hash="0" * 64,
        guest_expires_at=timezone.now() + timedelta(hours=1),
    )
    item = SessionItem.objects.create(
        session=session, content_version=version, order=1, snapshot={"skill": "speaking"}
    )
    fresh_job = AIJob.objects.create(
        kind=AIJobKind.WRITING_FEEDBACK, status=AIJobStatus.FAILED,
        session_item=item, provider="fake", model="m", prompt_version="v",
        run_after=timezone.now(), completed_at=timezone.now() - timedelta(days=1),
    )

    call_command("retention", "--execute", "--ai-failed-after-days", "30", stdout=StringIO())

    assert AssessmentSession.objects.filter(pk=session.pk).exists()
    assert AIJob.objects.filter(pk=fresh_job.pk).exists()


def test_age_arguments_are_bounded():
    with pytest.raises(CommandError):
        call_command("retention", "--guest-expired-after-hours", "0")
    with pytest.raises(CommandError):
        call_command("retention", "--guest-expired-after-hours", "10000")
    with pytest.raises(CommandError):
        call_command("retention", "--ai-failed-after-days", "0")
    with pytest.raises(CommandError):
        call_command("retention", "--ai-failed-after-days", "99999")
