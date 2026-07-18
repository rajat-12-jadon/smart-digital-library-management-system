"""
tests/test_auth.py

Tests for auth/auth_service.py and auth/password_utils.py -- the
highest-value things to test, since login/password logic is the most
security-sensitive code in the project.
"""

import pytest

from auth.auth_service import login, change_own_password, AuthenticationError
from auth.password_utils import hash_password, verify_password
from tests.helpers import create_user


def test_password_hashing_roundtrip():
    """A correct password should verify successfully against its own hash."""
    hashed = hash_password("MySecret123!")
    assert verify_password("MySecret123!", hashed) is True


def test_password_hashing_rejects_wrong_password():
    hashed = hash_password("MySecret123!")
    assert verify_password("WrongPassword", hashed) is False


def test_hash_password_rejects_empty_string():
    """Empty passwords should never be allowed to be hashed and stored."""
    with pytest.raises(ValueError):
        hash_password("")


def test_login_succeeds_with_correct_credentials():
    create_user("Test Student", "student@test.com", "Password123", "student")

    user = login("student@test.com", "Password123")

    assert user.email == "student@test.com"
    assert user.role == "student"


def test_login_fails_with_wrong_password():
    create_user("Test Student", "student@test.com", "Password123", "student")

    with pytest.raises(AuthenticationError):
        login("student@test.com", "WrongPassword")


def test_login_fails_with_unknown_email():
    with pytest.raises(AuthenticationError):
        login("nobody@nowhere.com", "whatever")


def test_login_is_case_insensitive_on_email():
    """Registered with lowercase email, login should still work with different casing."""
    create_user("Test Student", "student@test.com", "Password123", "student")

    user = login("STUDENT@TEST.COM", "Password123")

    assert user.email == "student@test.com"


def test_change_own_password_rejects_wrong_current_password():
    user_id = create_user("Test Student", "student@test.com", "Password123", "student")

    with pytest.raises(ValueError):
        change_own_password(user_id, "WrongCurrentPassword", "NewPassword456")


def test_change_own_password_rejects_same_password():
    """New password must differ from current -- a Phase 6 requirement."""
    user_id = create_user("Test Student", "student@test.com", "Password123", "student")

    with pytest.raises(ValueError):
        change_own_password(user_id, "Password123", "Password123")


def test_change_own_password_succeeds_and_new_password_works():
    user_id = create_user("Test Student", "student@test.com", "Password123", "student")

    change_own_password(user_id, "Password123", "NewPassword456")

    # old password should no longer work
    with pytest.raises(AuthenticationError):
        login("student@test.com", "Password123")

    # new password should work
    user = login("student@test.com", "NewPassword456")
    assert user.email == "student@test.com"