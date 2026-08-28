"""Model-level tests: identifier normalisation, ownership, recovery codes."""
import pytest
from django.db import IntegrityError

from apps.accounts.models import LearnerProfile, RecoveryCode, User

pytestmark = pytest.mark.django_db


def test_identifier_is_normalised_case_insensitive():
    user = User.objects.create_user(identifier="  Wingz@Example.com ", password="secret1")
    assert user.identifier == "wingz@example.com"


def test_email_metadata_is_optional_and_blank_by_default():
    user = User.objects.create_user(identifier="Wingz", password="secret1")
    assert user.identifier == "wingz"
    assert user.email == ""
    # Email may be supplied explicitly as optional metadata.
    other = User.objects.create_user(
        identifier="other", password="secret1", email="Person@Example.com"
    )
    assert other.email == "Person@example.com"


def test_duplicate_identifier_rejected_case_insensitively():
    User.objects.create_user(identifier="learner", password="secret1")
    with pytest.raises(IntegrityError):
        User.objects.create_user(identifier="LEARNER", password="secret1")


def test_direct_model_save_normalises_and_database_rejects_case_variant():
    first = User(identifier="  DirectUser  ")
    first.set_password("secret1")
    first.save()
    assert first.identifier == "directuser"

    duplicate = User(identifier="DIRECTUSER")
    duplicate.set_password("secret1")
    with pytest.raises(IntegrityError):
        duplicate.save()


def test_password_is_hashed_not_stored_plaintext():
    user = User.objects.create_user(identifier="learner", password="secret1")
    assert user.password != "secret1"
    assert user.check_password("secret1")


def test_get_by_natural_key_normalises():
    User.objects.create_user(identifier="learner", password="secret1")
    assert User.objects.get_by_natural_key("LEARNER").identifier == "learner"


def test_profile_is_one_to_one_and_owned():
    user = User.objects.create_user(identifier="learner", password="secret1")
    profile = LearnerProfile.objects.create(user=user)
    assert profile.user_id == user.id
    assert user.profile == profile
    with pytest.raises(IntegrityError):
        LearnerProfile.objects.create(user=user)


def test_profile_target_for_prefers_override():
    user = User.objects.create_user(identifier="learner", password="secret1")
    profile = LearnerProfile.objects.create(user=user, target_level=8, target_writing=10)
    assert profile.target_for("writing") == 10
    assert profile.target_for("reading") == 8


def test_profile_defaults():
    user = User.objects.create_user(identifier="learner", password="secret1")
    profile = LearnerProfile.objects.create(user=user)
    assert profile.target_level == 9
    assert profile.daily_minutes == 30
    assert profile.preferred_weekdays == [1, 2, 3, 4, 5]
    assert profile.timezone == "America/Toronto"


def test_recovery_code_hashes_and_matches():
    user = User.objects.create_user(identifier="learner", password="secret1")
    plaintext = RecoveryCode.generate_plaintext()
    code = RecoveryCode.objects.create(
        user=user, code_hash=RecoveryCode.hash_code(plaintext)
    )
    assert code.code_hash != plaintext
    assert code.matches(plaintext)
    assert not code.matches("wrong-code")
    assert not code.is_used
