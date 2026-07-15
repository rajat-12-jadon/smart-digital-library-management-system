"""
modules/books/book_service.py

All the book-related database logic lives here. The UI (book_ui.py)
never touches the database directly - it just calls these functions.
Same pattern as auth_service.py from Phase 2.
"""

import logging

from database import get_connection

logger = logging.getLogger(__name__)


class DuplicateISBNError(Exception):
    # raised when someone tries to add a book with an ISBN that
    # already exists - the DB itself blocks this via UNIQUE constraint,
    # this just turns that into a friendlier error for the UI to catch
    pass


def add_book(title, author, category, publisher, isbn, edition, total_quantity):
    """
    Adds a new book. available_quantity starts equal to total_quantity
    since all copies are available when a book is first added.
    """
    if not title or not author:
        raise ValueError("Title and author are required.")

    if total_quantity < 0:
        raise ValueError("Quantity cannot be negative.")

    with get_connection() as conn:
        with conn.cursor() as cur:
            try:
                cur.execute(
                    """
                    INSERT INTO Books
                        (title, author, category, publisher, isbn, edition,
                         total_quantity, available_quantity)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING book_id
                    """,
                    (
                        title, author, category, publisher, isbn, edition,
                        total_quantity, total_quantity,  # available = total at first
                    ),
                )
                new_id = cur.fetchone()[0]
            except Exception as e:
                # unique_violation is psycopg2's error for a UNIQUE
                # constraint break - that's how we know it's the ISBN,
                # not some other random DB error
                if "unique" in str(e).lower():
                    raise DuplicateISBNError(f"A book with ISBN '{isbn}' already exists.")
                raise
        conn.commit()

    logger.info("Book added: book_id=%s title=%s", new_id, title)
    return new_id


def get_all_books():
    """Returns every book as a list of dicts, ordered by title."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT book_id, title, author, category, publisher,
                       isbn, edition, total_quantity, available_quantity
                FROM Books
                ORDER BY title
                """
            )
            rows = cur.fetchall()

    # turning tuples into dicts so the UI can use column names
    # instead of remembering row[0], row[1], etc.
    books = []
    for row in rows:
        books.append({
            "book_id": row[0],
            "title": row[1],
            "author": row[2],
            "category": row[3],
            "publisher": row[4],
            "isbn": row[5],
            "edition": row[6],
            "total_quantity": row[7],
            "available_quantity": row[8],
        })
    return books


def search_books(keyword):
    """
    Searches title, author, and isbn for a partial match. ILIKE is
    Postgres's case-insensitive LIKE, so "harry" matches "Harry Potter".
    """
    keyword_pattern = f"%{keyword}%"

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT book_id, title, author, category, publisher,
                       isbn, edition, total_quantity, available_quantity
                FROM Books
                WHERE title ILIKE %s OR author ILIKE %s OR isbn ILIKE %s
                ORDER BY title
                """,
                (keyword_pattern, keyword_pattern, keyword_pattern),
            )
            rows = cur.fetchall()

    books = []
    for row in rows:
        books.append({
            "book_id": row[0],
            "title": row[1],
            "author": row[2],
            "category": row[3],
            "publisher": row[4],
            "isbn": row[5],
            "edition": row[6],
            "total_quantity": row[7],
            "available_quantity": row[8],
        })
    return books


def delete_book(book_id):
    """
    Deletes a book by id. Checks first if it's currently issued to
    anyone - if so, refuses to delete (don't want to lose the issue
    history, or let a book vanish while someone still has it).
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(*) FROM Book_Issue
                WHERE book_id = %s AND status = 'issued'
                """,
                (book_id,),
            )
            active_issues = cur.fetchone()[0]

            if active_issues > 0:
                raise ValueError(
                    "Cannot delete this book - it is currently issued to a student."
                )

            cur.execute("DELETE FROM Books WHERE book_id = %s", (book_id,))
        conn.commit()

    logger.info("Book deleted: book_id=%s", book_id)


def update_book(book_id, title, author, category, publisher, isbn, edition, total_quantity):
    """
    Updates an existing book's details. Also adjusts available_quantity
    if total_quantity changed, keeping the difference the same (e.g. if
    3 of 5 were available and total goes from 5 to 7, available becomes 5).
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            # need the current numbers first to work out the new
            # available_quantity
            cur.execute(
                "SELECT total_quantity, available_quantity FROM Books WHERE book_id = %s",
                (book_id,),
            )
            row = cur.fetchone()
            if row is None:
                raise ValueError(f"No book found with id {book_id}")

            old_total, old_available = row
            issued_count = old_total - old_available
            new_available = total_quantity - issued_count

            if new_available < 0:
                raise ValueError(
                    "New total quantity is less than the number of copies currently issued."
                )

            try:
                cur.execute(
                    """
                    UPDATE Books
                    SET title = %s, author = %s, category = %s, publisher = %s,
                        isbn = %s, edition = %s, total_quantity = %s,
                        available_quantity = %s
                    WHERE book_id = %s
                    """,
                    (
                        title, author, category, publisher, isbn, edition,
                        total_quantity, new_available, book_id,
                    ),
                )
            except Exception as e:
                if "unique" in str(e).lower():
                    raise DuplicateISBNError(f"A book with ISBN '{isbn}' already exists.")
                raise
        conn.commit()

    logger.info("Book updated: book_id=%s", book_id)