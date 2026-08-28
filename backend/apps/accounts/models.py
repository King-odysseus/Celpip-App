"""Account domain models: the custom user, learner profile, and recovery code.

The user is intentionally minimal. Registration is deliberately low-friction
(a single identifier plus a password), but storage and sessions are not: the
identifier is unique and case-insensitive, passwords are hashed with Argon2 by
Django, and recovery codes are stored only as salted hashes.
"""
from __future__ import annotations

import hashlib
import secrets
from typing import Any

from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone

# CELPIP components are reported on a 0–12 range; a target of 0 is not useful,
# so profiles accept 1–12 for the overall and per-skill targets.
MIN_TARGET_LEVEL = 1
MAX_TARGET_LEVEL = 12

# Number of random bytes behind a recovery code. 32 bytes ≈ 256 bits of entropy,
# rendered as a URL-safe token the learner sees exactly once.
RECOVERY_CODE_BYTES = 32


class UserManager(BaseUserManager):
    """Creates users keyed on a normalised, case-insensitive identifier."""

    use_in_migrations = True

    @staticmethod
    def normalize_identifier(identifier: str) -> str:
        """Trim surrounding whitespace and fold case so lookups are stable."""
        return identifier.strip().lower() if identifier else identifier

    def _create_user(
        self, identifier: str, password: str | None, **extra_fields: object
    ) -> User:
        if not identifier:
            raise ValueError("Users must have an identifier.")
        identifier = self.normalize_identifier(identifier)
        email = extra_fields.pop("email", "") or ""
        if email:
            email = self.normalize_email(email)
        user = self.model(identifier=identifier, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(
        self, identifier: str, password: str | None = None, **extra_fields: object
    ) -> User:
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(identifier, password, **extra_fields)

    def create_superuser(
        self, identifier: str, password: str | None = None, **extra_fields: object
    ) -> User:
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self._create_user(identifier, password, **extra_fields)

    def get_by_natural_key(self, identifier: str) -> User:
        return self.get(identifier=self.normalize_identifier(identifier))


class User(AbstractBaseUser, PermissionsMixin):
    """A learner account identified by one case-insensitive string.

    ``identifier`` may be anything the learner types — a username or an email.
    ``email`` is optional metadata used only to offer email-based recovery
    later; it is never required to register or practise.
    """

    identifier = models.CharField(
        max_length=254,
        unique=True,
        help_text="Case-insensitive login value; may be a username or an email.",
    )
    email = models.EmailField(
        blank=True,
        help_text="Optional. Enables email recovery; not required to register.",
    )
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = "identifier"
    REQUIRED_FIELDS: list[str] = []

    class Meta:
        verbose_name = "user"
        verbose_name_plural = "users"
        constraints = [
            models.UniqueConstraint(
                Lower("identifier"),
                name="accounts_user_identifier_ci_unique",
            )
        ]

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Keep direct ORM/admin writes consistent with the login manager."""
        self.identifier = UserManager.normalize_identifier(self.identifier)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.identifier


class Skill(models.TextChoices):
    LISTENING = "listening", "Listening"
    READING = "reading", "Reading"
    WRITING = "writing", "Writing"
    SPEAKING = "speaking", "Speaking"


def default_preferred_weekdays() -> list[int]:
    """Weekdays a learner plans to study, as ISO integers (Mon=1 … Sun=7)."""
    return [1, 2, 3, 4, 5]


def _target_validators() -> list:
    return [MinValueValidator(MIN_TARGET_LEVEL), MaxValueValidator(MAX_TARGET_LEVEL)]


class LearnerProfile(models.Model):
    """Study preferences and targets attached one-to-one to a user.

    One ``target_level`` acts as the default across all four skills; the
    per-skill fields are optional overrides for learners whose immigration
    requirements differ by skill.
    """

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="profile"
    )

    exam_date = models.DateField(
        null=True, blank=True, help_text="Planned CELPIP test date, if known."
    )

    target_level = models.PositiveSmallIntegerField(
        default=9,
        validators=_target_validators(),
        help_text="Default target CELPIP level (1–12) across all skills.",
    )
    target_listening = models.PositiveSmallIntegerField(
        null=True, blank=True, validators=_target_validators()
    )
    target_reading = models.PositiveSmallIntegerField(
        null=True, blank=True, validators=_target_validators()
    )
    target_writing = models.PositiveSmallIntegerField(
        null=True, blank=True, validators=_target_validators()
    )
    target_speaking = models.PositiveSmallIntegerField(
        null=True, blank=True, validators=_target_validators()
    )

    daily_minutes = models.PositiveSmallIntegerField(
        default=30,
        validators=[MinValueValidator(5), MaxValueValidator(600)],
        help_text="Minutes of study the learner plans per study day.",
    )
    preferred_weekdays = models.JSONField(
        default=default_preferred_weekdays,
        help_text="ISO weekday numbers (Mon=1 … Sun=7) the learner will study.",
    )
    timezone = models.CharField(
        max_length=64,
        default="America/Toronto",
        help_text="IANA timezone used for countdowns and daily plan boundaries.",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"Profile for {self.user.identifier}"

    def target_for(self, skill: str) -> int:
        """Return the per-skill override if set, else the default target."""
        override = getattr(self, f"target_{skill}", None)
        return override if override is not None else self.target_level


class RecoveryCode(models.Model):
    """A single, hashed, one-time recovery code per user.

    The plaintext code is shown to the learner exactly once at generation. Only
    its hash is stored, so a database leak does not expose usable codes.
    """

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="recovery_code"
    )
    code_hash = models.CharField(max_length=128)
    created_at = models.DateTimeField(auto_now_add=True)
    used_at = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        state = "used" if self.used_at else "active"
        return f"Recovery code for {self.user.identifier} ({state})"

    @staticmethod
    def generate_plaintext() -> str:
        """Return a fresh high-entropy, URL-safe recovery code."""
        return secrets.token_urlsafe(RECOVERY_CODE_BYTES)

    @staticmethod
    def hash_code(plaintext: str) -> str:
        """Hash a recovery code with Django's configured password hasher.

        The plaintext is already high-entropy random, but hashing keeps stored
        values non-reversible and consistent with the recovery-token policy.
        """
        return make_password(plaintext)

    def matches(self, plaintext: str) -> bool:
        return check_password(plaintext, self.code_hash)

    @property
    def is_used(self) -> bool:
        return self.used_at is not None


def fingerprint_identifier(identifier: str) -> str:
    """Stable, non-reversible key for throttling/audit without storing the raw value."""
    normalized = UserManager.normalize_identifier(identifier) or ""
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
