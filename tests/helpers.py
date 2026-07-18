"""
tests/helpers.py

Small helper functions used by multiple test files to set up data
quickly (e.g. "create a student to issue a book to"). Not a test file
itself -- pytest ignores files that don't start with test_.
"""

from database import get_connection
from auth.password_utils import hash_password


def create_user(name, email, password, role):
    """Directly inserts a user, bypassing the UI -- returns the new user_id."""
    hashed = hash_password(password)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO Users (name, email, password, role)
                VALUES (%s, %s, %s, %s)
                RETURNING user_id
                """,
                (name, email, hashed, role),
            )
            user_id = cur.fetchone()[0]
        conn.commit()

    return user_id


def create_book(title, total_quantity, isbn=None, author="Test Author"):
    """Directly inserts a book -- returns the new book_id."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO Books (title, author, isbn, total_quantity, available_quantity)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING book_id
                """,
                (title, author, isbn, total_quantity, total_quantity),
            )
            book_id = cur.fetchone()[0]
        conn.commit()

    return book_id