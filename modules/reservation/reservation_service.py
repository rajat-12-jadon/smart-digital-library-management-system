"""
modules/reservation/reservation_service.py

Reservation logic. A student can only reserve a book that's currently
unavailable (0 copies left) -- if copies are available, they should
just be issued the book directly, not reserve it.

fulfill_next_reservation() is called from return_book() (Phase 8) --
it does NOT issue the book automatically (that's a deliberate design
choice, see Phase 9 discussion). It just marks the oldest pending
reservation as fulfilled, so the student can see "this book is ready
for you" and the librarian can issue it manually when they come in.
"""

import logging

from database import get_connection

logger = logging.getLogger(__name__)


def held_copy_count(cur, book_id):
    """
    Counts how many copies of this book are earmarked for a specific
    student via a fulfilled-but-uncollected reservation -- i.e. copies
    that are back in available_quantity (see issue_service.return_book,
    which always increments it now), but shouldn't be handed to just
    anyone through the normal Issue Book flow. "Uncollected" means
    issue_id is still NULL (see issue_reserved_book(), which sets it
    once a reservation is actually collected).

    Shared by reserve_book() (below) and issue_service.issue_book() --
    lives here rather than in issue_service.py to avoid a circular
    import, since issue_service already imports from this module.
    """
    cur.execute(
        "SELECT COUNT(*) FROM Reservation WHERE book_id = %s AND status = 'fulfilled' AND issue_id IS NULL",
        (book_id,),
    )
    return cur.fetchone()[0]


def reserve_book(student_id, book_id):
    """
    Reserves a book for a student. Only allowed if there's no
    EFFECTIVELY available copy for a walk-in student -- that's
    available_quantity minus copies already held for someone else's
    pending pickup, not just the raw available_quantity. Without this
    distinction, a student could be told "just issue it directly" for
    a copy that's actually earmarked for someone ahead of them in line.
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT available_quantity FROM Books WHERE book_id = %s FOR UPDATE",
                (book_id,),
            )
            row = cur.fetchone()
            if row is None:
                raise ValueError("Book not found.")

            available_quantity = row[0]
            held_count = held_copy_count(cur, book_id)
            effective_available = available_quantity - held_count

            if effective_available > 0:
                raise ValueError(
                    "This book currently has copies available -- it can be issued directly."
                )

            cur.execute(
                """
                SELECT COUNT(*) FROM Reservation
                WHERE student_id = %s AND book_id = %s AND status = 'pending'
                """,
                (student_id, book_id),
            )
            already_reserved = cur.fetchone()[0]
            if already_reserved > 0:
                raise ValueError("You already have a pending reservation for this book.")

            # also block if a PAST reservation for this student+book was
            # already fulfilled but never actually collected -- without
            # this check, a student could end up with two separate
            # "ready for pickup" entries for the same book (one bug
            # found through real testing: this caused duplicate
            # reminder emails for the same book)
            cur.execute(
                """
                SELECT COUNT(*) FROM Reservation
                WHERE student_id = %s AND book_id = %s
                AND status = 'fulfilled' AND issue_id IS NULL
                """,
                (student_id, book_id),
            )
            already_waiting_for_pickup = cur.fetchone()[0]
            if already_waiting_for_pickup > 0:
                raise ValueError(
                    "This book is already reserved and waiting for you to pick up."
                )

            cur.execute(
                """
                INSERT INTO Reservation (student_id, book_id, status)
                VALUES (%s, %s, 'pending')
                RETURNING reservation_id
                """,
                (student_id, book_id),
            )
            new_id = cur.fetchone()[0]
        conn.commit()

    logger.info("Reservation created: reservation_id=%s student_id=%s book_id=%s", new_id, student_id, book_id)
    return new_id


def fulfill_next_reservation(cur, book_id):
    """
    Called from WITHIN return_book()'s transaction (that's why this
    takes a cursor `cur` as an argument, instead of opening its own
    connection like every other function here -- it needs to run as
    part of the SAME atomic transaction as the return, not a separate
    one). Finds the OLDEST pending reservation for this book (FIFO --
    First In, First Out) and marks it fulfilled.

    Returns the student_id who got fulfilled, or None if nobody had
    this book reserved.
    """
    cur.execute(
        """
        SELECT reservation_id, student_id FROM Reservation
        WHERE book_id = %s AND status = 'pending'
        ORDER BY reservation_date ASC
        LIMIT 1
        FOR UPDATE
        """,
        (book_id,),
    )
    row = cur.fetchone()
    if row is None:
        return None

    reservation_id, student_id = row

    cur.execute(
        "UPDATE Reservation SET status = 'fulfilled' WHERE reservation_id = %s",
        (reservation_id,),
    )

    logger.info(
        "Reservation fulfilled: reservation_id=%s student_id=%s book_id=%s",
        reservation_id, student_id, book_id,
    )
    return student_id


def get_reservations_for_student(student_id):
    """Returns a student's own reservations, newest first, with book title."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT r.reservation_id, b.title, r.reservation_date, r.status
                FROM Reservation r
                JOIN Books b ON r.book_id = b.book_id
                WHERE r.student_id = %s
                ORDER BY r.reservation_date DESC
                """,
                (student_id,),
            )
            rows = cur.fetchall()

    reservations = []
    for row in rows:
        reservations.append({
            "reservation_id": row[0],
            "book_title": row[1],
            "reservation_date": row[2],
            "status": row[3],
        })
    return reservations