"""
modules/librarians/librarian_service.py

Librarian-related database logic. Same pattern as student_service.py --
librarians live in the Users table (role='librarian'), just filtered
differently. Deliberately simpler than students: no "currently issued
book" or "unpaid fine" checks before delete, since those concepts don't
apply to librarians.
"""

import logging

from database import get_connection
from auth.password_utils import hash_password

logger = logging.getLogger(__name__)


class DuplicateEmailError(Exception):
    pass


def register_librarian(name, email, phone, password):
    """Creates a new librarian account. Password gets hashed before storage."""
    if not name or not email or not password:
        raise ValueError("Name, email, and password are required.")

    email = email.strip().lower()
    hashed = hash_password(password)

    with get_connection() as conn:
        with conn.cursor() as cur:
            try:
                cur.execute(
                    """
                    INSERT INTO Users (name, email, phone, password, role, force_password_change)
                    VALUES (%s, %s, %s, %s, 'librarian', TRUE)
                    RETURNING user_id
                    """,
                    (name, email, phone, hashed),
                )
                new_id = cur.fetchone()[0]
            except Exception as e:
                if "unique" in str(e).lower():
                    raise DuplicateEmailError(f"A user with email '{email}' already exists.")
                raise
        conn.commit()

    logger.info("Librarian registered: user_id=%s email=%s", new_id, email)
    return new_id


def get_all_librarians():
    """Returns every librarian (role='librarian') as a list of dicts."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT user_id, name, email, phone, created_at
                FROM Users
                WHERE role = 'librarian'
                ORDER BY name
                """
            )
            rows = cur.fetchall()

    return _rows_to_dicts(rows)


def search_librarians(keyword):
    """Searches name and email for a partial match (case-insensitive)."""
    keyword_pattern = f"%{keyword}%"

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT user_id, name, email, phone, created_at
                FROM Users
                WHERE role = 'librarian' AND (name ILIKE %s OR email ILIKE %s)
                ORDER BY name
                """,
                (keyword_pattern, keyword_pattern),
            )
            rows = cur.fetchall()

    return _rows_to_dicts(rows)


def update_librarian(user_id, name, email, phone):
    """Updates name/email/phone. Password is intentionally not touched here."""
    email = email.strip().lower()

    with get_connection() as conn:
        with conn.cursor() as cur:
            try:
                cur.execute(
                    """
                    UPDATE Users
                    SET name = %s, email = %s, phone = %s
                    WHERE user_id = %s AND role = 'librarian'
                    """,
                    (name, email, phone, user_id),
                )
            except Exception as e:
                if "unique" in str(e).lower():
                    raise DuplicateEmailError(f"A user with email '{email}' already exists.")
                raise

            if cur.rowcount == 0:
                raise ValueError(f"No librarian found with id {user_id}")
        conn.commit()

    logger.info("Librarian updated: user_id=%s", user_id)


def delete_librarian(user_id):
    """
    Deletes a librarian. No issued-book/fine checks needed here (those
    only apply to students) -- but we DO block deleting a librarian who
    has issued books to students in the past, since Book_Issue.librarian_id
    references them and deleting would break that history.
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM Book_Issue WHERE librarian_id = %s",
                (user_id,),
            )
            issue_history_count = cur.fetchone()[0]

            if issue_history_count > 0:
                raise ValueError(
                    "Cannot delete this librarian - they have book issue history on record."
                )

            cur.execute("DELETE FROM Users WHERE user_id = %s AND role = 'librarian'", (user_id,))
        conn.commit()

    logger.info("Librarian deleted: user_id=%s", user_id)


def reset_librarian_password(user_id, new_password):
    """Resets a librarian's password. Separate, explicit, logged action -- same reasoning as students."""
    if not new_password:
        raise ValueError("New password cannot be empty.")

    hashed = hash_password(new_password)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE Users SET password = %s, force_password_change = TRUE WHERE user_id = %s AND role = 'librarian'",
                (hashed, user_id),
            )
            if cur.rowcount == 0:
                raise ValueError(f"No librarian found with id {user_id}")

            cur.execute(
                "INSERT INTO Activity_Log (user_id, action) VALUES (%s, %s)",
                (user_id, "PASSWORD_RESET_BY_ADMIN"),
            )
        conn.commit()

    logger.info("Password reset for librarian user_id=%s", user_id)


def _rows_to_dicts(rows):
    librarians = []
    for row in rows:
        librarians.append({
            "user_id": row[0],
            "name": row[1],
            "email": row[2],
            "phone": row[3],
            "created_at": row[4],
        })
    return librarians