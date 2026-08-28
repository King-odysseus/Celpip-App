"""Write-oriented account operations.

Views stay thin: they validate transport input and delegate every state change
to one of these functions, each of which runs in a single transaction.
"""
from __future__ import annotations

from dataclasses import dataclass

from django.contrib.auth import authenticate
from django.core.validators import validate_email
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework_simplejwt.token_blacklist.models import (
    BlacklistedToken,
    OutstandingToken,
)

from .models import LearnerProfile, RecoveryCode, User, UserManager

MIN_PASSWORD_LENGTH = 6


class AccountError(Exception):
    """Base class for expected, message-safe account failures."""

    code = "account_error"

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        if code:
            self.code = code


class IdentifierTaken(AccountError):
    code = "identifier_taken"


class InvalidPassword(AccountError):
    code = "invalid_password"


class InvalidCredentials(AccountError):
    """Deliberately generic so it cannot confirm whether an account exists."""

    code = "invalid_credentials"


@dataclass(frozen=True)
class RegistrationResult:
    user: User
    recovery_code: str


def validate_password(password: str) -> None:
    """Enforce the launch policy: a six-character minimum, no composition puzzle."""
    if password is None or len(password) < MIN_PASSWORD_LENGTH:
        raise InvalidPassword(
            f"Password must be at least {MIN_PASSWORD_LENGTH} characters."
        )


def _looks_like_email(value: str) -> bool:
    try:
        validate_email(value)
    except Exception:
        return False
    return True


@transaction.atomic
def register_user(identifier: str, password: str) -> RegistrationResult:
    """Create a user, an empty profile, and a one-time recovery code.

    Accepts exactly an identifier and a password. When the identifier is itself
    a valid email, it is also stored as optional email metadata so email-based
    recovery can be offered later without a second registration field.
    """
    normalized = UserManager.normalize_identifier(identifier)
    if not normalized:
        raise AccountError("An identifier is required.", code="identifier_required")
    validate_password(password)

    email = normalized if _looks_like_email(normalized) else ""

    try:
        user = User.objects.create_user(
            identifier=normalized, password=password, email=email
        )
    except IntegrityError as exc:
        raise IdentifierTaken(
            "That identifier is already in use. Try another."
        ) from exc

    LearnerProfile.objects.create(user=user)
    recovery_code = issue_recovery_code(user)
    return RegistrationResult(user=user, recovery_code=recovery_code)


def issue_recovery_code(user: User) -> str:
    """Replace any existing recovery code and return the new plaintext once."""
    plaintext = RecoveryCode.generate_plaintext()
    RecoveryCode.objects.update_or_create(
        user=user,
        defaults={
            "code_hash": RecoveryCode.hash_code(plaintext),
            "used_at": None,
        },
    )
    return plaintext


def authenticate_user(identifier: str, password: str) -> User:
    """Return the user for valid credentials or raise a generic error.

    The same error is raised whether the identifier is unknown or the password
    is wrong, so responses never reveal whether an account exists.
    """
    normalized = UserManager.normalize_identifier(identifier or "")
    user = authenticate(username=normalized, password=password)
    if user is None or not user.is_active:
        raise InvalidCredentials("Invalid identifier or password.")
    return user


@transaction.atomic
def reset_password_with_recovery_code(
    identifier: str, recovery_code: str, new_password: str
) -> str:
    """Consume a one-time recovery code and set a new password.

    Returns a freshly issued recovery code (the old one is now spent). All
    failures raise the same generic error so the endpoint cannot be used to
    enumerate accounts or probe which half of the pair was wrong.
    """
    validate_password(new_password)
    normalized = UserManager.normalize_identifier(identifier or "")

    generic = InvalidCredentials("Invalid identifier or recovery code.")

    user = (
        User.objects.select_for_update()
        .filter(identifier=normalized, is_active=True)
        .first()
    )
    if user is None:
        raise generic

    stored = RecoveryCode.objects.select_for_update().filter(user=user).first()
    if stored is None or stored.is_used or not recovery_code:
        raise generic
    if not stored.matches(recovery_code):
        raise generic

    user.set_password(new_password)
    user.save(update_fields=["password"])

    # Password recovery is an account-takeover boundary. Revoke every refresh
    # session, not merely the browser performing the reset. Existing access
    # tokens are rejected by SimpleJWT's password-hash revocation check.
    for outstanding in OutstandingToken.objects.filter(user=user):
        BlacklistedToken.objects.get_or_create(token=outstanding)

    stored.used_at = timezone.now()
    stored.save(update_fields=["used_at"])

    # Issue a replacement so the learner is never left without a recovery path.
    return issue_recovery_code(user)


@transaction.atomic
def update_profile(profile: LearnerProfile, **fields: object) -> LearnerProfile:
    """Apply validated field updates to a profile and persist them."""
    for name, value in fields.items():
        setattr(profile, name, value)
    profile.full_clean(
        exclude=[f.name for f in profile._meta.fields if f.name not in fields]
    )
    profile.save()
    return profile
