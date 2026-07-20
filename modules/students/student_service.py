"""
modules/students/student_service.py

Student-related database logic. Students live in the Users table
(role='student') - same table Phase 2's login uses, just filtered here.
Same pattern as book_service.py: UI never touches the DB directly.
"""

import logging

from database import get_connection
from auth.password_utils import hash_password

logger = logging.getLogger(__name__)


class DuplicateEmailError(Exception):
    # same idea as DuplicateISBNError in book_service.py -- turns the
    # DB's UNIQUE constraint violation into a friendlier error for the UI
    pass


def register_student(name, email, phone, password):
    """
    Creates a new student account. Password gets hashed here (reusing
    Phase 2's hash_password) before it ever touches the database.
    """
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
                    VALUES (%s, %s, %s, %s, 'student', TRUE)
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

    logger.info("Student registered: user_id=%s email=%s", new_id, email)
    return new_id


def get_all_students():
    """Returns every student (role='student') as a list of dicts."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT user_id, name, email, phone, created_at
                FROM Users
                WHERE role = 'student'
                ORDER BY name
                """
            )
            rows = cur.fetchall()

    return _rows_to_dicts(rows)


def search_students(keyword):
    """Searches name and email for a partial match (case-insensitive)."""
    keyword_pattern = f"%{keyword}%"

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT user_id, name, email, phone, created_at
                FROM Users
                WHERE role = 'student' AND (name ILIKE %s OR email ILIKE %s)
                ORDER BY name
                """,
                (keyword_pattern, keyword_pattern),
            )
            rows = cur.fetchall()

    return _rows_to_dicts(rows)


def update_student(user_id, name, email, phone):
    """
    Updates name/email/phone. Password is deliberately NOT changed
    here -- that should be a separate, explicit "change password"
    action later, not something that silently happens as part of a
    routine profile edit.
    """
    email = email.strip().lower()

    with get_connection() as conn:
        with conn.cursor() as cur:
            try:
                cur.execute(
                    """
                    UPDATE Users
                    SET name = %s, email = %s, phone = %s
                    WHERE user_id = %s AND role = 'student'
                    """,
                    (name, email, phone, user_id),
                )
            except Exception as e:
                if "unique" in str(e).lower():
                    raise DuplicateEmailError(f"A user with email '{email}' already exists.")
                raise

            if cur.rowcount == 0:
                raise ValueError(f"No student found with id {user_id}")
        conn.commit()

    logger.info("Student updated: user_id=%s", user_id)


def delete_student(user_id):
    """
    Deletes a student. Refuses if they currently have a book issued
    or an unpaid fine -- same "protect data integrity" reasoning as
    book_service.delete_book().
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(*) FROM Book_Issue
                WHERE student_id = %s AND status = 'issued'
                """,
                (user_id,),
            )
            active_issues = cur.fetchone()[0]

            if active_issues > 0:
                raise ValueError(
                    "Cannot delete this student - they currently have a book issued."
                )

            cur.execute(
                """
                SELECT COUNT(*) FROM Fine f
                JOIN Book_Issue bi ON f.issue_id = bi.issue_id
                WHERE bi.student_id = %s AND f.paid = FALSE
                """,
                (user_id,),
            )
            unpaid_fines = cur.fetchone()[0]

            if unpaid_fines > 0:
                raise ValueError(
                    "Cannot delete this student - they have an unpaid fine."
                )

            try:
                cur.execute(
                    "DELETE FROM Users WHERE user_id = %s AND role = 'student'", (user_id,)
                )
            except Exception as e:
                # catches any OTHER foreign key still pointing at this
                # user that we didn't explicitly check for above (e.g.
                # Book_Issue history from books they've already
                # returned -- that's real borrowing history worth
                # keeping, not something to silently lose). Checking
                # for "foreign key" in the error text is the same
                # pattern used elsewhere in this project for "unique"
                # violations -- catch the DB's own integrity error
                # rather than re-implementing every possible check by hand.
                if "foreign key" in str(e).lower():
                    raise ValueError(
                        "Cannot delete this student - they have book issue history "
                        "on record that must be preserved."
                    )
                raise
        conn.commit()

    logger.info("Student deleted: user_id=%s", user_id)


def reset_student_password(user_id, new_password):
    """
    Resets a student's password. Deliberately kept SEPARATE from
    update_student() -- password changes are a more sensitive action
    than editing name/email/phone, and deserve their own explicit,
    logged action rather than being bundled into a routine profile
    edit where it could happen accidentally.
    """
    if not new_password:
        raise ValueError("New password cannot be empty.")

    hashed = hash_password(new_password)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE Users SET password = %s, force_password_change = TRUE WHERE user_id = %s AND role = 'student'",
                (hashed, user_id),
            )
            if cur.rowcount == 0:
                raise ValueError(f"No student found with id {user_id}")

            # log this specifically -- password resets are exactly the
            # kind of action that should be auditable later (who reset
            # whose password, and when)
            cur.execute(
                "INSERT INTO Activity_Log (user_id, action) VALUES (%s, %s)",
                (user_id, "PASSWORD_RESET_BY_LIBRARIAN"),
            )
        conn.commit()

    logger.info("Password reset for student user_id=%s", user_id)


def _rows_to_dicts(rows):
    # small helper so get_all_students and search_students don't
    # repeat the same tuple-to-dict conversion twice
    students = []
    for row in rows:
        students.append({
            "user_id": row[0],
            "name": row[1],
            "email": row[2],
            "phone": row[3],
            "created_at": row[4],
        })
    return students