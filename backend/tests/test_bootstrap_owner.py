"""Tests for the bootstrap_owner management command."""
import datetime as dt

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.accounts.models import User

pytestmark = pytest.mark.django_db


def test_bootstrap_creates_owner_with_default_exam_date():
    call_command("bootstrap_owner", "--identifier=owner", "--password=secret1")
    user = User.objects.get(identifier="owner")
    # The 10 October 2026 default is applied without being a global constant.
    assert user.profile.exam_date == dt.date(2026, 10, 10)


def test_bootstrap_accepts_custom_exam_date_and_target():
    call_command(
        "bootstrap_owner",
        "--identifier=owner",
        "--password=secret1",
        "--exam-date=2027-01-15",
        "--target-level=11",
    )
    user = User.objects.get(identifier="owner")
    assert user.profile.exam_date == dt.date(2027, 1, 15)
    assert user.profile.target_level == 11


def test_bootstrap_rerun_updates_and_resets_password():
    call_command("bootstrap_owner", "--identifier=owner", "--password=secret1")
    call_command(
        "bootstrap_owner",
        "--identifier=OWNER",
        "--password=changed1",
        "--exam-date=2027-02-02",
    )
    user = User.objects.get(identifier="owner")
    assert user.check_password("changed1")
    assert user.profile.exam_date == dt.date(2027, 2, 2)
    assert User.objects.filter(identifier="owner").count() == 1


def test_bootstrap_requires_password():
    with pytest.raises(CommandError):
        call_command("bootstrap_owner", "--identifier=owner")
