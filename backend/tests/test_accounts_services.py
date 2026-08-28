"""Service-layer tests for registration, recovery, and password rules."""
import pytest

from apps.accounts import services
from apps.accounts.models import LearnerProfile, RecoveryCode

pytestmark = pytest.mark.django_db


def test_register_creates_user_profile_and_recovery_code():
    result = services.register_user("learner", "secret1")
    assert result.user.identifier == "learner"
    assert result.recovery_code
    assert LearnerProfile.objects.filter(user=result.user).exists()
    assert RecoveryCode.objects.filter(user=result.user).exists()


def test_register_derives_email_metadata_from_email_identifier():
    result = services.register_user("Wingz@Example.com", "secret1")
    assert result.user.identifier == "wingz@example.com"
    assert result.user.email == "wingz@example.com"


def test_register_leaves_email_blank_for_username_identifier():
    result = services.register_user("wingz", "secret1")
    assert result.user.email == ""


def test_register_rejects_short_password():
    with pytest.raises(services.InvalidPassword):
        services.register_user("learner", "short")


def test_register_duplicate_raises_identifier_taken():
    services.register_user("learner", "secret1")
    with pytest.raises(services.IdentifierTaken):
        services.register_user("LEARNER", "secret1")


def test_authenticate_user_generic_on_failure():
    services.register_user("learner", "secret1")
    with pytest.raises(services.InvalidCredentials):
        services.authenticate_user("learner", "wrong-one")
    with pytest.raises(services.InvalidCredentials):
        services.authenticate_user("ghost", "whatever")


def test_issue_recovery_code_replaces_previous():
    result = services.register_user("learner", "secret1")
    first = RecoveryCode.objects.get(user=result.user)
    services.issue_recovery_code(result.user)
    second = RecoveryCode.objects.get(user=result.user)
    assert first.code_hash != second.code_hash
