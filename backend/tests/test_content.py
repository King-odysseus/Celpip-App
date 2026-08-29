"""Editorial workflow, public-content safety, and starter-bank tests."""
from io import StringIO

import pytest
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.accounts.models import User
from apps.content.models import (
    Choice,
    ContentItem,
    ContentVersion,
    PublicationStatus,
    Question,
    SourceType,
    TaskType,
)
from apps.content.services import publish, retire, submit_for_review

pytestmark = pytest.mark.django_db


@pytest.fixture
def reviewer():
    return User.objects.create_user(
        identifier="human-reviewer", password="secret1", is_staff=True
    )


@pytest.fixture
def draft(reviewer):
    task_type = TaskType.objects.create(
        code="reading-test-task",
        skill="reading",
        title="Test task",
        part_number=1,
        description="A test task.",
    )
    author = User.objects.create_user(identifier="content-author", password="secret1")
    item = ContentItem.objects.create(
        slug="original-test-set",
        task_type=task_type,
        title="Original test set",
        topic="Testing",
        difficulty=1,
        estimated_level=5,
        source_type=SourceType.AI_GENERATED,
        author=author,
        provenance="Original fixture authored for automated tests.",
    )
    version = ContentVersion.objects.create(
        item=item,
        version=1,
        instructions="Read and answer.",
        stimulus={"type": "article", "body": "An original passage."},
    )
    question = Question.objects.create(
        content_version=version,
        order=1,
        stem="What is this?",
        skill_focus="gist",
        evidence="The passage says so.",
        explanation="This identifies the gist.",
    )
    Choice.objects.create(
        question=question,
        order=1,
        text="Correct",
        is_correct=True,
        explanation="Supported by the passage.",
    )
    Choice.objects.create(
        question=question,
        order=2,
        text="Incorrect",
        is_correct=False,
        explanation="Not supported by the passage.",
    )
    return version


def test_ai_content_requires_independent_active_staff_reviewer(draft):
    submitted = submit_for_review(draft)

    with pytest.raises(ValidationError, match="active human staff"):
        publish(submitted, reviewer=draft.item.author)

    draft.item.author.is_staff = True
    draft.item.author.save(update_fields=["is_staff"])
    with pytest.raises(ValidationError, match="independent human review"):
        publish(submitted, reviewer=draft.item.author)


def test_valid_editorial_lifecycle(draft, reviewer):
    submitted = submit_for_review(draft)
    published = publish(submitted, reviewer=reviewer)

    assert published.status == PublicationStatus.PUBLISHED
    assert published.reviewer == reviewer
    assert published.reviewed_at is not None
    assert published.published_at is not None

    retired = retire(published)
    assert retired.status == PublicationStatus.RETIRED


def test_publish_rejects_invalid_answer_key(draft, reviewer):
    Choice.objects.filter(question__content_version=draft).update(is_correct=False)
    submitted = submit_for_review(draft)

    with pytest.raises(ValidationError) as error:
        publish(submitted, reviewer=reviewer)

    assert "invalid_answer_key" in error.value.message_dict


def test_published_version_and_children_are_immutable(draft, reviewer):
    question = draft.questions.get()
    choice = question.choices.first()
    published = publish(submit_for_review(draft), reviewer=reviewer)

    published.instructions = "Changed"
    with pytest.raises(ValidationError, match="immutable"):
        published.save()

    question.stem = "Changed"
    with pytest.raises(ValidationError, match="immutable"):
        question.save()

    choice.text = "Changed"
    with pytest.raises(ValidationError, match="immutable"):
        choice.save()


def test_seed_is_idempotent_and_has_reviewed_original_bank():
    first = StringIO()
    second = StringIO()
    call_command("seed_reading_content", stdout=first)
    call_command("seed_reading_content", stdout=second)

    assert "created 8" in first.getvalue()
    assert "created 0" in second.getvalue()
    assert TaskType.objects.filter(skill="reading").count() == 4
    assert ContentItem.objects.count() == 8
    assert ContentVersion.objects.filter(status="published").count() == 8
    assert Question.objects.count() == 24
    assert Choice.objects.count() == 96
    assert not ContentItem.objects.exclude(source_type=SourceType.AI_GENERATED).exists()
    assert not ContentVersion.objects.filter(reviewer_id=None).exists()
    author_ids = ContentItem.objects.values_list("author_id", flat=True)
    assert not ContentVersion.objects.filter(reviewer_id__in=author_ids).exists()


def test_public_catalog_and_detail_do_not_leak_answers(api_client):
    call_command("seed_reading_content", verbosity=0)

    catalog = api_client.get("/api/v1/content/reading/")
    assert catalog.status_code == 200
    assert catalog.json()["count"] == 8

    filtered = api_client.get(
        "/api/v1/content/reading/",
        {"task_type": "reading_correspondence", "difficulty": "1"},
    )
    assert filtered.status_code == 200
    assert len(filtered.json()["results"]) == 1

    detail = api_client.get("/api/v1/content/reading/garden-plot-renewal/")
    assert detail.status_code == 200
    payload = detail.json()
    serialized = str(payload)
    assert len(payload["questions"]) == 3
    assert "is_correct" not in serialized
    assert "explanation" not in serialized
    assert "evidence" not in serialized


def test_public_api_omits_drafts_and_unknown_details_404(api_client, draft):
    catalog = api_client.get("/api/v1/content/reading/")
    assert catalog.status_code == 200
    assert catalog.json()["count"] == 0
    assert api_client.get(f"/api/v1/content/reading/{draft.item.slug}/").status_code == 404


def test_validate_content_command_passes_seed_and_fails_invalid_draft(draft):
    draft.instructions = ""
    draft.save(update_fields=["instructions"])
    with pytest.raises(CommandError, match="Content validation failed"):
        call_command("validate_content", stderr=StringIO())

    draft.instructions = "Read and answer."
    draft.save(update_fields=["instructions"])
    output = StringIO()
    call_command("validate_content", stdout=output)
    assert "Validated 1 content version" in output.getvalue()
