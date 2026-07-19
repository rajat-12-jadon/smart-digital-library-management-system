"""
auth/auth_service.py

Core login logic. This is the ONLY place in the app that should query
Users for authentication purposes -- the dashboard/UI layer calls
login() and gets back either a CurrentUser or an AuthenticationError,
never a raw DB row.
"""

import logging
import secrets
import string
from dataclasses import dataclass

from database import get_connection
from auth.password_utils import verify_password

logger = logging.getLogger(__name__)


class AuthenticationError(Exception):
    """
    Raised for any login failure. Deliberately generic -- we do not
    subclass this into "UserNotFound" / "WrongPassword" variants,
    because the UI layer must show the same message either way.
    Distinguishing them would leak whether an email is registered.
    """
    pass


@dataclass(frozen=True)
class CurrentUser:
    """
    Represents a logged-in session. Immutable (frozen) so nothing
    downstream can accidentally mutate "who's logged in" mid-session --
    e.g. an admin-management screen changing role on the object instead
    of in the database.
    """
    user_id: int
    name: str
    email: str
    role: str  # 'admin' | 'librarian' | 'student'
    force_password_change: bool = False


def login(email: str, password: str) -> CurrentUser:
    """
    Verify credentials and return a CurrentUser on success.
    Raises AuthenticationError on any failure (unknown email, wrong
    password, or empty input) -- callers should catch this single
    exception type and show one generic message.
    """
    email = (email or "").strip().lower()

    if not email or not password:
        raise AuthenticationError("Email and password are required.")

    with get_connection() as conn:
        with conn.cursor() as cur:
            # Parameterized query -- psycopg2 substitutes %s safely,
            # this is NOT string formatting. Never build SQL with
            # f-strings/.format()/%  with user input, that's how SQL
            # injection happens.
            cur.execute(
                """
                SELECT user_id, name, email, password, role, force_password_change
                FROM Users
                WHERE email = %s
                """,
                (email,),
            )
            row = cur.fetchone()

    if row is None:
        logger.info("Login attempt for unknown email: %s", email)
        raise AuthenticationError("Invalid email or password.")

    user_id, name, db_email, password_hash, role, force_password_change = row

    if not verify_password(password, password_hash):
        logger.info("Failed login attempt for user_id=%s", user_id)
        _log_activity(user_id, "FAILED_LOGIN")
        raise AuthenticationError("Invalid email or password.")

    logger.info("Successful login for user_id=%s (%s)", user_id, role)
    _log_activity(user_id, "LOGIN")

    return CurrentUser(
        user_id=user_id, name=name, email=db_email, role=role,
        force_password_change=force_password_change,
    )


def change_password(user_id: int, new_password: str) -> None:
    """
    Used when a user changes their OWN password (as opposed to
    reset_student_password / reset_librarian_password, which are an
    admin/librarian changing someone ELSE's password). Clears
    force_password_change so they aren't asked again next login.
    """
    from auth.password_utils import hash_password

    if not new_password:
        raise ValueError("New password cannot be empty.")

    with get_connection() as conn:
        with conn.cursor() as cur:
            # fetch the CURRENT password hash first, so we can check
            # whether the "new" password is actually the same as the
            # old one before wasting a hash computation on it
            cur.execute("SELECT password FROM Users WHERE user_id = %s", (user_id,))
            row = cur.fetchone()
            if row is None:
                raise ValueError(f"No user found with id {user_id}")

            current_hash = row[0]

            if verify_password(new_password, current_hash):
                raise ValueError(
                    "New password must be different from your current password."
                )

            hashed = hash_password(new_password)

            cur.execute(
                """
                UPDATE Users
                SET password = %s, force_password_change = FALSE
                WHERE user_id = %s
                """,
                (hashed, user_id),
            )
        conn.commit()

    logger.info("Password changed by user_id=%s", user_id)
    _log_activity(user_id, "PASSWORD_CHANGED_BY_SELF")


def change_own_password(user_id: int, current_password: str, new_password: str) -> None:
    """
    Used when a user VOLUNTARILY changes their own password from a
    dashboard (as opposed to change_password(), which is used by the
    forced first-login flow, right after login already verified who
    they are). This one requires re-entering the current password --
    a safeguard in case someone walks up to an unlocked/unattended
    session, they still can't lock the real owner out without knowing
    the current password.
    """
    if not current_password or not new_password:
        raise ValueError("Both current and new password are required.")

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT password FROM Users WHERE user_id = %s", (user_id,))
            row = cur.fetchone()
            if row is None:
                raise ValueError(f"No user found with id {user_id}")

            current_hash = row[0]

            if not verify_password(current_password, current_hash):
                raise ValueError("Current password is incorrect.")

            if verify_password(new_password, current_hash):
                raise ValueError(
                    "New password must be different from your current password."
                )

            from auth.password_utils import hash_password
            hashed = hash_password(new_password)

            cur.execute(
                """
                UPDATE Users
                SET password = %s, force_password_change = FALSE
                WHERE user_id = %s
                """,
                (hashed, user_id),
            )
        conn.commit()

    logger.info("Password voluntarily changed by user_id=%s", user_id)
    _log_activity(user_id, "PASSWORD_CHANGED_BY_SELF")


def forgot_password(email: str) -> None:
    """
    "Forgot Password" flow -- generates a random temporary password,
    sets it on the account, forces a change on next login (reusing
    the same force_password_change flag from Phase 6), and emails it
    to the user.

    Deliberately does NOT raise an error or reveal anything if the
    email doesn't exist -- same email-enumeration protection
    reasoning as login()'s generic error message. The UI should show
    the same "if that email exists, we sent something" message either
    way, so an attacker can't use this to check which emails are
    registered.
    """
    from auth.password_utils import hash_password
    from utils.email_utils import send_email, EmailConfigError

    email = (email or "").strip().lower()
    if not email:
        return

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT user_id, name FROM Users WHERE email = %s", (email,))
            row = cur.fetchone()

            if row is None:
                logger.info("Forgot-password requested for unknown email: %s", email)
                return  # silently do nothing -- see docstring

            user_id, name = row

            # random 12-character password from letters+digits -- not
            # meant to be memorable, the user is expected to change it
            # immediately (force_password_change=TRUE below enforces that)
            alphabet = string.ascii_letters + string.digits
            temp_password = "".join(secrets.choice(alphabet) for _ in range(12))
            hashed = hash_password(temp_password)

            cur.execute(
                """
                UPDATE Users
                SET password = %s, force_password_change = TRUE
                WHERE user_id = %s
                """,
                (hashed, user_id),
            )
        conn.commit()

    logger.info("Temporary password issued for user_id=%s", user_id)
    _log_activity(user_id, "PASSWORD_RESET_VIA_FORGOT_PASSWORD")

    try:
        send_email(
            email,
            "Your Smart Digital Library temporary password",
            f"Hi {name},\n\n"
            f"Your temporary password is: {temp_password}\n\n"
            f"You'll be asked to set a new password when you log in.\n\n"
            f"- Smart Digital Library",
        )
    except EmailConfigError:
        logger.error("Email not configured -- could not send temp password to %s", email)
    except Exception:
        logger.exception("Failed to send forgot-password email to %s", email)


def _log_activity(user_id: int, action: str) -> None:
    """
    Writes to Activity_Log. Kept as a small internal helper here for
    now since login/logout are the first activity-worthy events;
    Phase 13 (Reports) may promote this into its own
    modules/activity_logs/ service if more modules start needing it.
    """
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO Activity_Log (user_id, action) VALUES (%s, %s)",
                    (user_id, action),
                )
            conn.commit()
    except Exception:
        # Activity logging must never break login itself -- log and
        # swallow rather than raise.
        logger.exception("Failed to write activity log for user_id=%s", user_id)