"""Speaking Attempt 1 vs Attempt 2: retry linkage and comparison tests."""
from __future__ import annotations

import hashlib
import itertools
from datetime import timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import IntegrityError
from django.utils import timezone

from apps.accounts.models import LearnerProfile, User
from apps.ai_services.models import AIFeedback, AIJob, AIJobKind, AIJobStatus
from apps.assessments.models import (
    AssessmentSession,
    SessionItem,
    SpeakingRetry,
    SpeakingSubmission,
)
from apps.assessments.services import (
    ComparisonUnavailable,
    RetryNotAllowed,
    SessionNotActive,
    WrongSkill,
    create_speaking_retry,
    speaking_comparison,
)
from apps.assessments.storage import private_recording_storage
from apps.content.models import ContentItem, ContentVersion, PublicationStatus, TaskType

pytestmark = pytest.mark.django_db

SESSIONS_URL = "/api/v1/sessions/"

TEST_GUEST_TOKEN = "test-guest-token"
GUEST_HEADERS = {"HTTP_X_GUEST_TOKEN": TEST_GUEST_TOKEN}

_part_counter = itertools.count(1)


@pytest.fixture(autouse=True)
def isolated_recording_storage(tmp_path, monkeypatch):
    monkeypatch.setattr(private_recording_storage, "_location", str(tmp_path))
    private_recording_storage.__dict__.pop("base_location", None)
    private_recording_storage.__dict__.pop("location", None)
    yield tmp_path


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _make_content(skill: str = "speaking") -> ContentVersion:
    code = f"retry_{skill}_{uuid4().hex[:8]}"
    task_type = TaskType.objects.create(
        code=code,
        skill=skill,
        title="Retry prompt",
        part_number=next(_part_counter),
        description="",
        strategy=[],
        common_mistakes=[],
    )
    item = ContentItem.objects.create(
        slug=f"slug-{code}",
        task_type=task_type,
        title="Retry prompt",
        topic="t",
        difficulty=1,
        estimated_level=5,
        provenance="test",
    )
    return ContentVersion.objects.create(
        item=item,
        version=1,
        status=PublicationStatus.DRAFT,
        instructions="",
        stimulus={},
    )


def _make_session(
    *,
    user=None,
    skill="speaking",
    mode="practice",
    state="submitted",
    attempt_number=1,
    guest_token_hash=None,
    guest_expires_at=None,
):
    version = _make_content(skill)
    if user is None:
        if guest_token_hash is None:
            guest_token_hash = _token_hash(TEST_GUEST_TOKEN)
        if guest_expires_at is None:
            guest_expires_at = timezone.now() + timedelta(hours=1)
    session = AssessmentSession.objects.create(
        user=user,
        mode=mode,
        state=state,
        attempt_number=attempt_number,
        submitted_at=timezone.now() if state == "submitted" else None,
        guest_token_hash=guest_token_hash or "",
        guest_expires_at=guest_expires_at,
    )
    item = SessionItem.objects.create(
        session=session,
        content_version=version,
        order=1,
        snapshot={
            "skill": skill,
            "task_type": version.item.task_type_id,
            "title": version.item.title,
            "instructions": version.instructions,
            "stimulus": version.stimulus,
            "questions": [],
        },
    )
    return session, item


def _save_recording(item: SessionItem, name: str = "speaking/owned.webm"):
    stored = private_recording_storage.save(name, ContentFile(b"\x1aE\xdf\xa3private-audio"))
    submission = SpeakingSubmission.objects.create(
        session_item=item,
        audio=stored,
        mime_type="audio/webm",
        container="webm",
        byte_size=20,
        duration_ms=1000,
        revision=1,
        submitted_at=timezone.now(),
    )
    return submission, Path(submission.audio.path)


def _assessment(*, low=5, high=7, dimensions=None, strengths=None, priorities=None):
    return {
        "overall_summary": "Deterministic comparison fixture.",
        "dimensions": dimensions
        or [
            {
                "key": "content_coherence",
                "rating": 2,
                "evidence": "Coherent.",
                "next_step": "Organize ideas.",
            },
            {
                "key": "vocabulary",
                "rating": 2,
                "evidence": "Varied words.",
                "next_step": "Choose precise words.",
            },
            {"key": "delivery", "rating": 2, "evidence": "Clear pace.", "next_step": "Slow down."},
            {
                "key": "task_fulfillment",
                "rating": 2,
                "evidence": "Addressed task.",
                "next_step": "Cover every point.",
            },
        ],
        "strengths": strengths or ["A complete attempt."],
        "priorities": priorities or ["Review task instructions."],
        "estimated_level_low": low,
        "estimated_level_high": high,
        "confidence": "low",
        "disclaimer": "AI-assisted practice estimate — not an official CELPIP score.",
    }


def _make_feedback(item, *, assessment, provider="fake", model="m", prompt_version="v"):
    job = AIJob.objects.create(
        kind=AIJobKind.SPEAKING_FEEDBACK,
        status=AIJobStatus.SUCCEEDED,
        session_item=item,
        provider=provider,
        model=model,
        prompt_version=prompt_version,
        run_after=timezone.now(),
    )
    return AIFeedback.objects.create(
        session_item=item,
        job=job,
        kind=AIJobKind.SPEAKING_FEEDBACK,
        provider=provider,
        model=model,
        prompt_version=prompt_version,
        assessment=assessment,
    )


def _make_job(item, status, *, error_message="", error_code=""):
    return AIJob.objects.create(
        kind=AIJobKind.SPEAKING_FEEDBACK,
        status=status,
        session_item=item,
        provider="fake",
        model="m",
        prompt_version="v",
        run_after=timezone.now(),
        error_message=error_message,
        error_code=error_code,
    )


def _retry_url(session_id):
    return f"{SESSIONS_URL}{session_id}/speaking/retry/"


def _comparison_url(session_id):
    return f"{SESSIONS_URL}{session_id}/speaking/comparison/"


def _linked_pair(*, user=None, mode="practice", submit_retry=False):
    """Build a valid attempt-1/attempt-2 pair through the service.

    Going through :func:`create_speaking_retry` guarantees the link satisfies the
    hardened model invariants (same owner, mode, content version, and frozen
    snapshot). Optionally submit the retry so it counts as a completed attempt.
    """
    source, source_item = _make_session(user=user, mode=mode)
    retry, _ = create_speaking_retry(session=source)
    retry_item = retry.items.get()
    if submit_retry:
        retry.state = "submitted"
        retry.submitted_at = timezone.now()
        retry.save(update_fields=["state", "submitted_at"])
    return source, source_item, retry, retry_item


# ── Model invariants ───────────────────────────────────────────────────────


def test_attempt_number_defaults_to_one_and_retry_is_one_to_one():
    source, source_item, retry, _ = _linked_pair()
    assert source.attempt_number == 1
    assert retry.attempt_number == 2

    link = source.speaking_retry
    assert retry.speaking_retry_of == link

    # A second link from the same source is impossible at the DB level. Build a
    # second *valid* retry (so model validation passes) and let the one-to-one
    # uniqueness on ``source`` surface as an IntegrityError.
    other = AssessmentSession.objects.create(
        user=source.user,
        guest_token_hash=source.guest_token_hash,
        guest_expires_at=source.guest_expires_at,
        mode=source.mode,
        state="active",
        attempt_number=2,
    )
    SessionItem.objects.create(
        session=other,
        content_version=source_item.content_version,
        order=1,
        snapshot=source_item.snapshot,
    )
    with pytest.raises(IntegrityError):
        SpeakingRetry.objects.create(source=source, retry=other)


# ── Service invariants ─────────────────────────────────────────────────────


def test_create_retry_preserves_owner_mode_content_and_frozen_snapshot():
    user = User.objects.create_user(identifier="retry-owner", password="secret1")
    source, source_item = _make_session(user=user, mode="practice")
    source_snapshot = dict(source_item.snapshot)

    retry, replayed = create_speaking_retry(session=source)

    assert replayed is False
    assert retry.attempt_number == 2
    assert retry.state == "active"
    assert retry.user_id == user.pk
    assert retry.mode == source.mode

    retry_item = retry.items.get()
    assert retry_item.content_version_id == source_item.content_version_id
    assert retry_item.snapshot == source_snapshot

    # Source stays attempt 1 and unchanged.
    assert source.attempt_number == 1
    source.refresh_from_db()
    assert source.attempt_number == 1


def test_create_retry_rejects_active_non_speaking_mock_and_retry_of_retry():
    active, _ = _make_session(state="active")
    with pytest.raises(SessionNotActive):
        create_speaking_retry(session=active)

    non_speaking, _ = _make_session(skill="writing")
    with pytest.raises(WrongSkill):
        create_speaking_retry(session=non_speaking)

    mock, _ = _make_session(mode="mock")
    with pytest.raises(RetryNotAllowed):
        create_speaking_retry(session=mock)

    source, _, retry, _ = _linked_pair(submit_retry=True)
    with pytest.raises(RetryNotAllowed):
        create_speaking_retry(session=retry)


def test_create_retry_is_idempotent():
    source, _ = _make_session()
    first, replayed = create_speaking_retry(session=source)
    assert replayed is False

    second, replayed = create_speaking_retry(session=source)
    assert replayed is True
    assert second.pk == first.pk
    assert SpeakingRetry.objects.count() == 1


def test_retry_gets_fresh_relative_deadline_not_the_old_absolute_one():
    source, _ = _make_session(mode="practice")
    duration = timedelta(minutes=12)
    # A timed attempt-1 window that has already elapsed by the time of the retry.
    source.deadline_at = source.started_at + duration
    source.save(update_fields=["deadline_at"])

    before = timezone.now()
    retry, _ = create_speaking_retry(session=source)
    after = timezone.now()

    assert retry.deadline_at is not None
    # Attempt 2 receives a *new* window of the same length, measured from now.
    assert before + duration <= retry.deadline_at <= after + duration
    # It is never the stale absolute deadline copied from the source.
    assert retry.deadline_at != source.deadline_at
    assert retry.deadline_at > source.deadline_at


def test_retry_of_untimed_learn_source_stays_untimed():
    source, _ = _make_session(mode="learn")
    assert source.deadline_at is None

    retry, _ = create_speaking_retry(session=source)

    assert retry.mode == "learn"
    assert retry.deadline_at is None


# ── Direct model-link validation ───────────────────────────────────────────


def _valid_retry_session(source, source_item):
    """A standalone, unlinked attempt-2 session that is a valid retry of source."""
    retry = AssessmentSession.objects.create(
        user=source.user,
        guest_token_hash=source.guest_token_hash,
        guest_expires_at=source.guest_expires_at,
        mode=source.mode,
        state="active",
        attempt_number=2,
    )
    retry_item = SessionItem.objects.create(
        session=retry,
        content_version=source_item.content_version,
        order=1,
        snapshot=source_item.snapshot,
    )
    return retry, retry_item


def test_model_accepts_a_coherent_link_and_admin_deletion():
    user = User.objects.create_user(identifier="retry-valid", password="secret1")
    source, source_item = _make_session(user=user)
    retry, _ = _valid_retry_session(source, source_item)

    link = SpeakingRetry.objects.create(source=source, retry=retry)
    assert SpeakingRetry.objects.filter(pk=link.pk).exists()
    # Deletion of a valid link is never blocked.
    link.delete()
    assert not SpeakingRetry.objects.exists()


def test_model_rejects_same_session_as_source_and_retry():
    source, source_item = _make_session()
    with pytest.raises(ValidationError):
        SpeakingRetry.objects.create(source=source, retry=source)


def test_model_rejects_different_owner():
    owner = User.objects.create_user(identifier="retry-owner-a", password="secret1")
    other = User.objects.create_user(identifier="retry-owner-b", password="secret1")
    source, source_item = _make_session(user=owner)
    retry, _ = _valid_retry_session(source, source_item)
    retry.user = other
    retry.save(update_fields=["user"])
    with pytest.raises(ValidationError, match="owner"):
        SpeakingRetry.objects.create(source=source, retry=retry)


def test_model_rejects_mismatched_guest_identity():
    source, source_item = _make_session()
    retry, _ = _valid_retry_session(source, source_item)
    retry.guest_token_hash = _token_hash("a-different-guest")
    retry.save(update_fields=["guest_token_hash"])
    with pytest.raises(ValidationError, match="guest"):
        SpeakingRetry.objects.create(source=source, retry=retry)


def test_model_rejects_mismatched_mode():
    source, source_item = _make_session(mode="practice")
    retry, _ = _valid_retry_session(source, source_item)
    retry.mode = "learn"
    retry.save(update_fields=["mode"])
    with pytest.raises(ValidationError, match="mode"):
        SpeakingRetry.objects.create(source=source, retry=retry)


def test_model_rejects_wrong_attempt_numbers():
    source, source_item = _make_session(attempt_number=2)
    retry, _ = _valid_retry_session(source, source_item)
    with pytest.raises(ValidationError, match="attempt 1"):
        SpeakingRetry.objects.create(source=source, retry=retry)

    source2, source2_item = _make_session()
    retry2, _ = _valid_retry_session(source2, source2_item)
    retry2.attempt_number = 1
    retry2.save(update_fields=["attempt_number"])
    with pytest.raises(ValidationError, match="attempt 2"):
        SpeakingRetry.objects.create(source=source2, retry=retry2)


def test_model_rejects_unsubmitted_source_or_inactive_retry():
    source, source_item = _make_session(state="active")
    retry, _ = _valid_retry_session(source, source_item)
    with pytest.raises(ValidationError, match="submitted"):
        SpeakingRetry.objects.create(source=source, retry=retry)

    source2, source2_item = _make_session()
    retry2, _ = _valid_retry_session(source2, source2_item)
    retry2.state = "submitted"
    retry2.submitted_at = timezone.now()
    retry2.save(update_fields=["state", "submitted_at"])
    with pytest.raises(ValidationError, match="active"):
        SpeakingRetry.objects.create(source=source2, retry=retry2)


def test_model_rejects_non_speaking_sessions():
    source, source_item = _make_session(skill="writing")
    retry, _ = _valid_retry_session(source, source_item)
    with pytest.raises(ValidationError, match="speaking"):
        SpeakingRetry.objects.create(source=source, retry=retry)


def test_model_rejects_different_content_version():
    source, source_item = _make_session()
    retry, retry_item = _valid_retry_session(source, source_item)
    # Repoint the retry item at an entirely different frozen content version.
    other_version = _make_content("speaking")
    retry_item.content_version = other_version
    retry_item.snapshot = {**source_item.snapshot}
    retry_item.save(update_fields=["content_version", "snapshot"])
    with pytest.raises(ValidationError, match="content version"):
        SpeakingRetry.objects.create(source=source, retry=retry)


def test_model_rejects_mutated_frozen_snapshot():
    source, source_item = _make_session()
    retry, retry_item = _valid_retry_session(source, source_item)
    retry_item.snapshot = {**source_item.snapshot, "title": "tampered"}
    retry_item.save(update_fields=["snapshot"])
    with pytest.raises(ValidationError, match="snapshot"):
        SpeakingRetry.objects.create(source=source, retry=retry)


# ── Endpoint authorization and metadata ────────────────────────────────────


def test_retry_endpoint_owner_created_and_other_user_denied(api_client):
    owner = User.objects.create_user(identifier="retry-owner", password="secret1")
    source, _ = _make_session(user=owner)
    api_client.force_authenticate(owner)

    created = api_client.post(_retry_url(source.pk))
    assert created.status_code == 201
    body = created.json()
    assert body["attempt_number"] == 2
    assert body["replayed"] is False
    assert body["launch_url"] == f"/speaking/session/{body['id']}"

    stranger = User.objects.create_user(identifier="retry-stranger", password="secret1")
    api_client.force_authenticate(stranger)
    assert api_client.post(_retry_url(source.pk)).status_code == 403
    assert api_client.get(_comparison_url(source.pk)).status_code == 403


def test_guest_retry_reuses_token_hash_and_authorizes_both(api_client):
    token = "guest-token-shared-across-attempts"
    source, _ = _make_session(
        guest_token_hash=_token_hash(token),
        guest_expires_at=timezone.now() + timedelta(hours=1),
    )
    headers = {"HTTP_X_GUEST_TOKEN": token}

    created = api_client.post(_retry_url(source.pk), **headers)
    assert created.status_code == 201
    retry_id = created.json()["id"]
    # No plaintext token is ever returned or stored on the retry.
    assert "guest_token" not in created.json()

    retry = AssessmentSession.objects.get(pk=retry_id)
    assert retry.guest_token_hash == source.guest_token_hash
    assert retry.guest_expires_at == source.guest_expires_at

    # The same token authorizes the retry session.
    detail = api_client.get(f"{SESSIONS_URL}{retry_id}/speaking/", **headers)
    assert detail.status_code == 200
    # A wrong or missing token is refused.
    assert api_client.get(f"{SESSIONS_URL}{retry_id}/speaking/").status_code == 403


def test_speaking_detail_exposes_attempt_metadata_safely(api_client):
    source, _ = _make_session()
    created = api_client.post(_retry_url(source.pk), **GUEST_HEADERS)
    retry_id = created.json()["id"]

    source_detail = api_client.get(
        f"{SESSIONS_URL}{source.pk}/speaking/", **GUEST_HEADERS
    ).json()
    assert source_detail["attempt"] == {"attempt_number": 1, "retry_id": retry_id}

    retry_detail = api_client.get(
        f"{SESSIONS_URL}{retry_id}/speaking/", **GUEST_HEADERS
    ).json()
    assert retry_detail["attempt"] == {"attempt_number": 2, "source_id": str(source.pk)}


def test_retry_endpoint_replays_idempotently(api_client):
    source, _ = _make_session()
    first = api_client.post(_retry_url(source.pk), **GUEST_HEADERS)
    second = api_client.post(_retry_url(source.pk), **GUEST_HEADERS)

    assert first.status_code == 201
    assert second.status_code == 200
    assert second.json()["id"] == first.json()["id"]
    assert second.json()["replayed"] is True
    assert SpeakingRetry.objects.count() == 1


# ── Source immutability ────────────────────────────────────────────────────


def test_source_submission_and_audio_remain_immutable():
    source, source_item = _make_session()
    submission, path = _save_recording(source_item)

    create_speaking_retry(session=source)

    submission.refresh_from_db()
    submission.duration_ms += 1
    with pytest.raises(ValidationError, match="immutable"):
        submission.save()
    with pytest.raises(ValidationError, match="immutable"):
        submission.delete()
    assert path.exists()


# ── Comparison state machine ───────────────────────────────────────────────


def _pair():
    return _linked_pair()


def test_comparison_unavailable_for_unlinked_session(api_client):
    session, _ = _make_session()
    assert api_client.get(_comparison_url(session.pk), **GUEST_HEADERS).status_code == 404
    with pytest.raises(ComparisonUnavailable):
        speaking_comparison(session)


def test_comparison_pending_when_jobs_absent_or_queued(api_client):
    source, source_item, retry, retry_item = _pair()

    payload = speaking_comparison(source)
    assert payload["status"] == "pending"
    assert payload["attempts"]["1"]["feedback_status"] == "pending"
    assert payload["attempts"]["1"]["job_status"] is None

    _make_job(source_item, AIJobStatus.QUEUED)
    _make_job(retry_item, AIJobStatus.RUNNING)

    response = api_client.get(_comparison_url(source.pk), **GUEST_HEADERS)
    assert response.status_code == 200
    assert response.json()["status"] == "pending"
    assert response.json()["attempts"]["1"]["job_status"] == "queued"
    assert response.json()["attempts"]["2"]["job_status"] == "running"


def test_comparison_failed_when_either_job_failed(api_client):
    source, source_item, retry, retry_item = _pair()
    _make_job(
        source_item,
        AIJobStatus.FAILED,
        error_message="Safe failure.",
        error_code="provider_timeout",
    )

    response = api_client.get(_comparison_url(retry.pk), **GUEST_HEADERS)
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "failed"
    assert payload["attempts"]["1"]["feedback_status"] == "failed"
    assert payload["attempts"]["1"]["job_status"] == "failed"
    # Only a stable machine code and generic copy are exposed — never the raw text.
    assert payload["attempts"]["1"]["error_code"] == "provider_timeout"
    assert payload["attempts"]["1"]["error"] == (
        "AI-assisted feedback could not be completed for this attempt."
    )
    assert payload["attempts"]["2"]["feedback_status"] == "pending"


def test_comparison_failed_falls_back_to_generic_error_code():
    """A failed job without an explicit code still gets a stable fallback code."""
    source, source_item, retry, retry_item = _pair()
    _make_job(source_item, AIJobStatus.FAILED, error_message="boom", error_code="")

    payload = speaking_comparison(source)
    assert payload["attempts"]["1"]["error_code"] == "evaluation_failed"
    assert payload["attempts"]["1"]["error"] == (
        "AI-assisted feedback could not be completed for this attempt."
    )


def test_comparison_failed_never_leaks_raw_error_message():
    """The raw provider error text must never reach the comparison payload."""
    secret = "SECRET-MARKER-do-not-leak-42"
    source, source_item, retry, retry_item = _pair()
    _make_job(
        source_item,
        AIJobStatus.FAILED,
        error_message=f"Traceback with {secret} and snapshot fragments.",
        error_code="provider_error",
    )

    payload = speaking_comparison(source)
    assert payload["status"] == "failed"
    # The raw message (and its embedded secret) never reaches the payload.
    assert secret not in str(payload)
    assert payload["attempts"]["1"]["error_code"] == "provider_error"
    assert payload["attempts"]["1"]["error"] == (
        "AI-assisted feedback could not be completed for this attempt."
    )


# ── Ready comparison math, ordering, dedup, audit, privacy ─────────────────


def test_comparison_ready_math_order_dedup_audit_and_privacy(api_client):
    source, source_item, retry, retry_item = _pair()

    dims_1 = [
        {"key": "content_coherence", "rating": 2, "evidence": "A1-coh", "next_step": "A1-coh-next"},
        {"key": "vocabulary", "rating": 2, "evidence": "A1-voc", "next_step": "A1-voc-next"},
        {"key": "delivery", "rating": 3, "evidence": "A1-del", "next_step": "A1-del-next"},
        {"key": "task_fulfillment", "rating": 2, "evidence": "A1-tf", "next_step": "A1-tf-next"},
    ]
    dims_2 = [
        {"key": "content_coherence", "rating": 3, "evidence": "A2-coh", "next_step": "A2-coh-next"},
        {"key": "vocabulary", "rating": 2, "evidence": "A2-voc", "next_step": "A2-voc-next"},
        {"key": "delivery", "rating": 3, "evidence": "A2-del", "next_step": "A2-del-next"},
        {"key": "task_fulfillment", "rating": 4, "evidence": "A2-tf", "next_step": "A2-tf-next"},
    ]
    _make_feedback(
        source_item,
        assessment=_assessment(low=5, high=7, dimensions=dims_1),
        provider="p1",
        model="m1",
        prompt_version="v1",
    )
    _make_feedback(
        retry_item,
        assessment=_assessment(
            low=6,
            high=8,
            dimensions=dims_2,
            strengths=["S1", "S2"],
            priorities=["P1", "A2-voc-next"],
        ),
        provider="p2",
        model="m2",
        prompt_version="v2",
    )

    response = api_client.get(_comparison_url(source.pk), **GUEST_HEADERS)
    assert response.status_code == 200
    payload = response.json()

    assert payload["status"] == "ready"
    assert payload["attempt_1"]["estimated_range"] == {"low": 5, "high": 7}
    assert payload["attempt_1"]["estimated_midpoint"] == 6.0
    assert payload["attempt_2"]["estimated_range"] == {"low": 6, "high": 8}
    assert payload["attempt_2"]["estimated_midpoint"] == 7.0
    assert payload["midpoint_delta"] == 1.0

    # Per-dimension deltas in the canonical rubric order.
    assert [dim["key"] for dim in payload["dimension_deltas"]] == [
        "content_coherence",
        "vocabulary",
        "delivery",
        "task_fulfillment",
    ]
    assert payload["dimension_deltas"][0]["delta"] == 1
    assert payload["dimension_deltas"][1]["delta"] == 0
    assert payload["dimension_deltas"][2]["delta"] == 0
    assert payload["dimension_deltas"][3]["delta"] == 2
    # Speaking delivery is labelled "Listenability".
    assert payload["dimension_deltas"][2]["label"] == "Listenability"

    # Improvements: increased dimensions (labels + attempt 2 evidence), then strengths.
    assert payload["improvements"] == [
        {"kind": "dimension", "label": "Content/Coherence", "evidence": "A2-coh"},
        {"kind": "dimension", "label": "Task Fulfillment", "evidence": "A2-tf"},
        {"kind": "strength", "text": "S1"},
        {"kind": "strength", "text": "S2"},
    ]

    # Remaining priorities: current priorities then non-improved next steps, deduped.
    assert payload["remaining_priorities"] == ["P1", "A2-voc-next", "A2-del-next"]

    assert payload["attempt_1"]["audit"] == {
        "provider": "p1",
        "model": "m1",
        "prompt_version": "v1",
    }
    assert payload["attempt_2"]["audit"] == {
        "provider": "p2",
        "model": "m2",
        "prompt_version": "v2",
    }

    # Strong disclaimer and no raw audio paths or binary.
    assert "not an official CELPIP score" in payload["disclaimer"]
    assert "not an official score difference" in payload["disclaimer"]
    assert "audio" not in str(payload)
    assert ".webm" not in str(payload)
    assert "private_media" not in str(payload)


def test_comparison_is_symmetric_from_retry_side(api_client):
    source, source_item, retry, retry_item = _pair()
    _make_feedback(source_item, assessment=_assessment(low=4, high=6))
    _make_feedback(retry_item, assessment=_assessment(low=5, high=7))

    from_source = api_client.get(_comparison_url(source.pk), **GUEST_HEADERS).json()
    from_retry = api_client.get(_comparison_url(retry.pk), **GUEST_HEADERS).json()

    assert from_source["status"] == from_retry["status"] == "ready"
    assert from_source["midpoint_delta"] == from_retry["midpoint_delta"] == 1.0
    assert from_source["attempt_1"]["session_id"] == from_retry["attempt_1"]["session_id"]
    assert from_source["attempt_2"]["session_id"] == from_retry["attempt_2"]["session_id"]


def test_comparison_improvements_dedup_dimensions_then_strengths():
    """Improvements are deduped by normalized text, dimensions before strengths."""
    source, source_item, retry, retry_item = _pair()

    # Only content_coherence improves, yielding one dimension improvement whose
    # label ("Content/Coherence") a later strength duplicates.
    dims_1 = [
        {"key": "content_coherence", "rating": 1, "evidence": "e", "next_step": "n"},
        {"key": "vocabulary", "rating": 2, "evidence": "e", "next_step": "n"},
        {"key": "delivery", "rating": 2, "evidence": "e", "next_step": "n"},
        {"key": "task_fulfillment", "rating": 2, "evidence": "e", "next_step": "n"},
    ]
    dims_2 = [
        {"key": "content_coherence", "rating": 2, "evidence": "A2-coh", "next_step": "n"},
        {"key": "vocabulary", "rating": 2, "evidence": "e", "next_step": "n"},
        {"key": "delivery", "rating": 2, "evidence": "e", "next_step": "n"},
        {"key": "task_fulfillment", "rating": 2, "evidence": "e", "next_step": "n"},
    ]
    _make_feedback(source_item, assessment=_assessment(dimensions=dims_1))
    _make_feedback(
        retry_item,
        assessment=_assessment(
            dimensions=dims_2,
            # Strengths that duplicate the dimension label (case/whitespace
            # variants) and each other collapse to their first occurrence.
            strengths=["Content/Coherence", "  content/COHERENCE  ", "Great Job", "great job"],
        ),
    )

    payload = speaking_comparison(source)

    assert payload["improvements"] == [
        {"kind": "dimension", "label": "Content/Coherence", "evidence": "A2-coh"},
        {"kind": "strength", "text": "Great Job"},
    ]


# ── Concurrent retry creation ──────────────────────────────────────────────


def test_create_retry_replays_winner_on_concurrent_link_race(monkeypatch):
    """A losing concurrent insert replays the winner without orphaning a session."""
    user = User.objects.create_user(identifier="retry-race", password="secret1")
    source, source_item = _make_session(user=user, mode="practice")
    source.deadline_at = source.started_at + timedelta(minutes=10)
    source.save(update_fields=["deadline_at"])

    from apps.assessments import services as svc

    # Deterministically land a competing winner between this call's existence
    # check and its own insert. The source-window computation calls timezone.now
    # once, before the retry's inner savepoint opens, so the injected winning row
    # survives the loser's IntegrityError rollback.
    state: dict = {}
    real_now = svc.timezone.now

    def racing_now():
        if "done" not in state:
            state["done"] = True
            winner_retry, _ = _valid_retry_session(source, source_item)
            link = SpeakingRetry.objects.create(source=source, retry=winner_retry)
            state["retry_id"] = link.retry_id
        return real_now()

    monkeypatch.setattr(svc.timezone, "now", racing_now)

    retry, replayed = create_speaking_retry(session=source)

    assert replayed is True
    assert retry.pk == state["retry_id"]
    assert SpeakingRetry.objects.filter(source=source).count() == 1
    # The loser's attempt-2 session was rolled back — no orphan remains.
    assert AssessmentSession.objects.filter(attempt_number=2).count() == 1


def test_create_retry_rejects_non_positive_source_window():
    """A degenerate (<= 0) source time window cannot yield a usable retry."""
    source, _ = _make_session(mode="practice")
    source.deadline_at = source.started_at  # zero-length window
    source.save(update_fields=["deadline_at"])

    with pytest.raises(RetryNotAllowed):
        create_speaking_retry(session=source)


# ── Export linkage ─────────────────────────────────────────────────────────


def test_export_includes_attempt_and_linkage_ids_without_audio(api_client):
    user = User.objects.create_user(identifier="retry-exporter", password="secret1")
    LearnerProfile.objects.create(user=user)

    source, source_item, retry, retry_item = _linked_pair(user=user, submit_retry=True)
    _save_recording(source_item, name="speaking/export-source.webm")
    _save_recording(retry_item, name="speaking/export-retry.webm")

    api_client.force_authenticate(user)
    body = api_client.get("/api/v1/me/export/").json()

    by_id = {session["id"]: session for session in body["sessions"]}
    assert by_id[str(source.pk)]["attempt"] == {
        "attempt_number": 1,
        "retry_id": str(retry.pk),
    }
    assert by_id[str(retry.pk)]["attempt"] == {
        "attempt_number": 2,
        "source_id": str(source.pk),
    }

    serialized = str(body)
    assert "export-source.webm" not in serialized
    assert "export-retry.webm" not in serialized
    assert "guest_token_hash" not in serialized


# ── Deletion removes both recordings ───────────────────────────────────────


def test_account_deletion_removes_both_recordings(api_client):
    user = User.objects.create_user(identifier="retry-deleter", password="secret1")
    source, source_item, retry, retry_item = _linked_pair(user=user, submit_retry=True)

    source_submission, source_path = _save_recording(source_item, name="speaking/a.webm")
    retry_submission, retry_path = _save_recording(retry_item, name="speaking/b.webm")
    assert source_path.exists() and retry_path.exists()

    api_client.force_authenticate(user)
    resp = api_client.delete("/api/v1/me/", {"password": "secret1"}, format="json")
    assert resp.status_code == 204

    assert not AssessmentSession.objects.filter(user_id=user.pk).exists()
    assert not SpeakingSubmission.objects.exists()
    assert not SpeakingRetry.objects.exists()
    assert not source_path.exists()
    assert not retry_path.exists()


def test_delete_source_session_cascades_link_and_keeps_retry_session():
    source, source_item, retry, _ = _linked_pair()

    source.delete()

    assert not SpeakingRetry.objects.exists()
    assert AssessmentSession.objects.filter(pk=retry.pk).exists()
    with pytest.raises(SpeakingRetry.DoesNotExist):
        SpeakingRetry.objects.get(retry=retry)


# ── Dashboard volume and independent progress ──────────────────────────────


def test_both_attempts_count_and_progress_stays_independent():
    from apps.learning.services import _completed_attempts, progress_payload

    user = User.objects.create_user(identifier="retry-dashboard", password="secret1")
    source, source_item, retry, retry_item = _linked_pair(user=user, submit_retry=True)

    # Both submitted sessions count toward focused-attempt volume.
    assert _completed_attempts(user) == 2

    # Independent feedback artifacts each contribute one attempt and are
    # averaged together (5.0 and 7.0 midpoints), never collapsed into one row.
    _make_feedback(source_item, assessment=_assessment(low=4, high=6))
    _make_feedback(retry_item, assessment=_assessment(low=6, high=8))

    progress = progress_payload(user)
    speaking = next(s for s in progress["skills"] if s["skill"] == "speaking")
    assert speaking["attempts"] == 2
    assert speaking["estimate_low"] == 5.0
    assert speaking["estimate_high"] == 7.0
