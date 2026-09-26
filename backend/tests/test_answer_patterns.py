"""Answer patterns: coverage, exam-condition withholding, drills, and grading."""

from types import SimpleNamespace

import pytest
from django.core.management import call_command

from apps.accounts.models import User
from apps.ai_services.contracts import ProviderResult
from apps.ai_services.providers import FakeProvider
from apps.ai_services.schemas import validate_exemplar, validate_feedback
from apps.assessments.views import _answer_pattern
from apps.content.answer_patterns import ANSWER_PATTERNS, grading_pattern
from apps.content.models import TaskType
from apps.learning.models import PatternDrillProgress

pytestmark = pytest.mark.django_db


@pytest.fixture
def seeded():
    call_command("seed_speaking_content", verbosity=0)
    call_command("seed_writing_content", verbosity=0)


def test_every_speaking_and_writing_task_type_has_a_pattern(seeded):
    codes = set(
        TaskType.objects.filter(skill__in=["speaking", "writing"]).values_list("code", flat=True)
    )
    assert codes == set(ANSWER_PATTERNS)
    for pattern in ANSWER_PATTERNS.values():
        # The feedback schema allows at most six pattern_check entries.
        assert 2 <= len(pattern["steps"]) <= 6
        assert all(step["phrases"] for step in pattern["steps"])


def test_task_type_api_includes_the_pattern(api_client, seeded):
    response = api_client.get("/api/v1/content/task-types/?skill=speaking")
    advice = next(item for item in response.json() if item["code"] == "speaking_advice")
    assert advice["answer_pattern"]["mnemonic"] == "CARE"


@pytest.mark.parametrize(
    ("mode", "shown"),
    [("practice", True), ("learn", True), ("mock", False), ("diagnostic", False)],
)
def test_pattern_is_withheld_under_exam_conditions(mode, shown):
    session = SimpleNamespace(mode=mode)
    item = SimpleNamespace(snapshot={"task_type": "writing_email"})
    assert (_answer_pattern(session, item) is not None) is shown


def test_drill_results_build_a_mastery_streak(api_client, seeded):
    user = User.objects.create_user(identifier="driller", password="secret1")
    api_client.force_authenticate(user)

    for correct in (True, False, True, True, True):
        response = api_client.post(
            "/api/v1/me/pattern-drills/",
            {"task_type": "speaking_advice", "correct": correct},
            format="json",
        )
        assert response.status_code == 200

    progress = PatternDrillProgress.objects.get(user=user, task_type_id="speaking_advice")
    assert (progress.attempts, progress.correct, progress.streak) == (5, 4, 3)
    listing = api_client.get("/api/v1/me/pattern-drills/").json()["results"]
    assert listing[0]["mastered"] is True


def test_drills_reject_task_types_without_a_pattern(api_client):
    user = User.objects.create_user(identifier="driller-2", password="secret1")
    api_client.force_authenticate(user)
    response = api_client.post(
        "/api/v1/me/pattern-drills/",
        {"task_type": "reading_correspondence", "correct": True},
        format="json",
    )
    assert response.status_code == 400


def test_drills_require_an_account(api_client):
    response = api_client.get("/api/v1/me/pattern-drills/")
    assert response.status_code in (401, 403)


def test_grader_output_keeps_well_formed_pattern_checks():
    payload = FakeProvider().grade_text(
        {"skill": "writing", "response": "Hi.", "answer_pattern": grading_pattern("writing_email")}
    ).payload
    payload["pattern_check"].append({"step": "Bogus", "followed": "yes"})

    checked = validate_feedback(payload)["pattern_check"]

    assert [item["step"] for item in checked] == [
        "Direct greeting",
        "Explain your purpose",
        "Answer every point",
        "Request and sign off",
    ]


def test_example_step_labels_must_quote_the_response():
    exemplar = FakeProvider().generate_exemplar(
        {"answer_pattern": grading_pattern("speaking_advice")}
    ).payload
    exemplar["pattern_map"].append({"step": "Reassure", "excerpt": "not in the answer"})

    mapped = validate_exemplar(exemplar)["pattern_map"]

    assert all(item["excerpt"] in exemplar["response"] for item in mapped)
    assert [item["step"] for item in mapped] == ["Connect", "Advise", "Add"]


def test_feedback_and_example_jobs_receive_the_pattern(
    api_client, seeded, django_capture_on_commit_callbacks
):
    from apps.ai_services.models import AIJob, AIJobKind
    from apps.ai_services.services import claim_next_job, run_job

    started = api_client.post(
        "/api/v1/sessions/",
        {"content_slug": "email-noisy-renovation", "mode": "practice", "time_limit_seconds": 600},
        format="json",
    )
    headers = {"HTTP_X_GUEST_TOKEN": started.json()["guest_token"]}
    session_id = started.json()["id"]
    assert (
        api_client.get(f"/api/v1/sessions/{session_id}/writing/", **headers).json()[
            "answer_pattern"
        ]["mnemonic"]
        == "DEAR"
    )
    with django_capture_on_commit_callbacks(execute=True):
        api_client.post(
            f"/api/v1/sessions/{session_id}/writing/submit/",
            {"text": "Dear manager, I am writing about the noise."},
            format="json",
            **headers,
        )
    feedback_job = AIJob.objects.get(kind=AIJobKind.WRITING_FEEDBACK)
    assert feedback_job.input_snapshot["answer_pattern"]["mnemonic"] == "DEAR"

    class RecordingProvider(FakeProvider):
        seen: list = []

        def generate_exemplar(self, payload):
            self.seen.append(payload.get("answer_pattern"))
            return super().generate_exemplar(payload)

        def grade_text(self, payload):
            result = super().grade_text(payload)
            return ProviderResult(
                result.payload | {"estimated_level_low": 11, "estimated_level_high": 12}
            )

    with django_capture_on_commit_callbacks(execute=True):
        run_job(claim_next_job(), provider=FakeProvider())
    example_job = AIJob.objects.get(kind=AIJobKind.RESPONSE_EXEMPLAR)
    provider = RecordingProvider()
    finished = run_job(example_job, provider=provider)
    assert provider.seen[0]["mnemonic"] == "DEAR"
    assert finished.output["pattern_map"]
