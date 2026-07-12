"""
auth/auth_service.py

Core login logic. This is the ONLY place in the app that should query
Users for authentication purposes -- the dashboard/UI layer calls
login() and gets back either a CurrentUser or an AuthenticationError,
never a raw DB row.
"""

import logging
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
                SELECT user_id, name, email, password, role
                FROM Users
                WHERE email = %s
                """,
                (email,),
            )
            row = cur.fetchone()

    if row is None:
        logger.info("Login attempt for unknown email: %s", email)
        raise AuthenticationError("Invalid email or password.")

    user_id, name, db_email, password_hash, role = row

    if not verify_password(password, password_hash):
        logger.info("Failed login attempt for user_id=%s", user_id)
        _log_activity(user_id, "FAILED_LOGIN")
        raise AuthenticationError("Invalid email or password.")

    logger.info("Successful login for user_id=%s (%s)", user_id, role)
    _log_activity(user_id, "LOGIN")

    return CurrentUser(user_id=user_id, name=name, email=db_email, role=role)


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