"""
modules/issue_return/issue_service.py

Handles issuing books to students. The core operation here (reduce
quantity + insert issue record) MUST happen as a single atomic
transaction -- if one succeeds and the other fails, the data becomes
inconsistent (e.g. quantity reduced but no record of who has the book).
This is the first place in the project where get_connection()'s
transaction guarantee (from Phase 1) actually matters in practice.
"""

import logging
from datetime import date, timedelta

from database import get_connection
from config import FINE_RULES
from modules.reservation.reservation_service import fulfill_next_reservation

logger = logging.getLogger(__name__)

# how many days a student gets to return a book. kept as a constant
# here (not buried in the middle of issue_book) so it's easy to find
# and change later, and easy to reuse if a "preview due date" UI
# feature gets added
ISSUE_PERIOD_DAYS = 14


def issue_book(student_id, librarian_id, book_id):
    """
    Issues a book to a student. Everything here happens inside ONE
    connection/transaction -- all the checks, the quantity update, and
    the insert either all succeed together (commit) or none of them
    take effect (rollback happens automatically via get_connection()
    if any exception is raised partway through).
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            # lock the book's row for this transaction (FOR UPDATE) so
            # two librarians issuing the same last copy at the same
            # moment can't both succeed -- the second one waits until
            # the first transaction commits, then sees the updated
            # (now zero) quantity and fails cleanly instead of both
            # succeeding and quantity going negative
            cur.execute(
                "SELECT available_quantity FROM Books WHERE book_id = %s FOR UPDATE",
                (book_id,),
            )
            row = cur.fetchone()
            if row is None:
                raise ValueError("Book not found.")

            available_quantity = row[0]
            if available_quantity <= 0:
                raise ValueError("This book is not currently available.")

            # don't let a student have two active copies of the same
            # book issued at once
            cur.execute(
                """
                SELECT COUNT(*) FROM Book_Issue
                WHERE student_id = %s AND book_id = %s AND status = 'issued'
                """,
                (student_id, book_id),
            )
            already_issued = cur.fetchone()[0]
            if already_issued > 0:
                raise ValueError("This student already has this book issued.")

            issue_date = date.today()
            due_date = issue_date + timedelta(days=ISSUE_PERIOD_DAYS)

            cur.execute(
                """
                INSERT INTO Book_Issue
                    (student_id, librarian_id, book_id, issue_date, due_date, status)
                VALUES (%s, %s, %s, %s, %s, 'issued')
                RETURNING issue_id
                """,
                (student_id, librarian_id, book_id, issue_date, due_date),
            )
            new_issue_id = cur.fetchone()[0]

            cur.execute(
                "UPDATE Books SET available_quantity = available_quantity - 1 WHERE book_id = %s",
                (book_id,),
            )
        conn.commit()

    logger.info(
        "Book issued: issue_id=%s student_id=%s book_id=%s due_date=%s",
        new_issue_id, student_id, book_id, due_date,
    )
    return new_issue_id, due_date


def return_book(issue_id):
    """
    Returns a book. Like issue_book(), this is one atomic transaction:
    mark the issue as returned, increase the book's available quantity,
    and (if late) create a Fine record -- all together or not at all.

    Returns (late_days, fine_amount, fulfilled_student_id) so the UI
    can tell the librarian whether a fine was created and whether a
    waiting student's reservation is now ready.
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT book_id, due_date, status FROM Book_Issue
                WHERE issue_id = %s
                FOR UPDATE
                """,
                (issue_id,),
            )
            row = cur.fetchone()
            if row is None:
                raise ValueError("Issue record not found.")

            book_id, due_date, status = row

            if status != "issued":
                raise ValueError("This book has already been returned.")

            return_date = date.today()
            late_days = max(0, (return_date - due_date).days)

            cur.execute(
                """
                UPDATE Book_Issue
                SET return_date = %s, status = 'returned'
                WHERE issue_id = %s
                """,
                (return_date, issue_id),
            )

            # check reservations BEFORE touching available_quantity --
            # if someone has this book reserved, this copy is HELD for
            # them, not added back to the general available pool.
            # otherwise a different student could grab it via the normal
            # Issue Book screen before the reserved student collects it.
            fulfilled_student_id = fulfill_next_reservation(cur, book_id)

            if fulfilled_student_id is None:
                cur.execute(
                    "UPDATE Books SET available_quantity = available_quantity + 1 WHERE book_id = %s",
                    (book_id,),
                )
            # else: quantity intentionally NOT increased -- this copy
            # is reserved. See issue_reserved_book() for how it
            # eventually gets handed to the waiting student.

            fine_amount = None
            if late_days > 0:
                fine_amount = _calculate_fine(late_days)
                cur.execute(
                    """
                    INSERT INTO Fine (issue_id, late_days, fine_amount, paid)
                    VALUES (%s, %s, %s, FALSE)
                    """,
                    (issue_id, late_days, fine_amount),
                )
        conn.commit()

    logger.info(
        "Book returned: issue_id=%s late_days=%s fine=%s reservation_fulfilled_for=%s",
        issue_id, late_days, fine_amount, fulfilled_student_id,
    )
    return late_days, fine_amount, fulfilled_student_id


def _calculate_fine(late_days):
    """
    Looks up the per-day rate for how late the return is, using the
    FINE_RULES slabs from config.py, then multiplies by the days late.
    Kept as a private helper since only return_book() needs it right
    now -- if a "preview fine before returning" UI feature gets added
    later, this can be made public.
    """
    for min_days, max_days, rate_per_day in FINE_RULES:
        if max_days is None:  # the "16+" slab, no upper bound
            if late_days >= min_days:
                return late_days * rate_per_day
        elif min_days <= late_days <= max_days:
            return late_days * rate_per_day

    # shouldn't happen since FINE_RULES covers 1 to infinity, but a
    # safe fallback is better than a silent None slipping through
    return 0


def issue_reserved_book(reservation_id, librarian_id):
    """
    Hands a HELD copy (see return_book()) to the student whose
    reservation was fulfilled. Deliberately does NOT touch
    available_quantity -- that copy was never added back to the
    general pool in the first place, so there's nothing to subtract.

    No new "collected" status is needed on Reservation -- once a
    matching Book_Issue record with status='issued' exists for this
    student+book, that itself is the signal that the reservation was
    actually picked up (see get_pending_pickups()'s query).
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT student_id, book_id, status FROM Reservation WHERE reservation_id = %s FOR UPDATE",
                (reservation_id,),
            )
            row = cur.fetchone()
            if row is None:
                raise ValueError("Reservation not found.")

            student_id, book_id, status = row
            if status != "fulfilled":
                raise ValueError("This reservation isn't ready for pickup.")

            issue_date = date.today()
            due_date = issue_date + timedelta(days=ISSUE_PERIOD_DAYS)

            cur.execute(
                """
                INSERT INTO Book_Issue
                    (student_id, librarian_id, book_id, issue_date, due_date, status)
                VALUES (%s, %s, %s, %s, %s, 'issued')
                RETURNING issue_id
                """,
                (student_id, librarian_id, book_id, issue_date, due_date),
            )
            new_issue_id = cur.fetchone()[0]
        conn.commit()

    logger.info("Reserved book issued: reservation_id=%s issue_id=%s", reservation_id, new_issue_id)
    return new_issue_id, due_date


def get_pending_pickups():
    """
    Returns fulfilled reservations that haven't actually been picked
    up yet -- i.e. no matching 'issued' Book_Issue exists for that
    student+book combination. This is what a librarian would check to
    know "who's waiting to collect a book that's ready for them".
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT r.reservation_id, u.name, b.title, r.reservation_date
                FROM Reservation r
                JOIN Users u ON r.student_id = u.user_id
                JOIN Books b ON r.book_id = b.book_id
                WHERE r.status = 'fulfilled'
                AND NOT EXISTS (
                    SELECT 1 FROM Book_Issue bi
                    WHERE bi.student_id = r.student_id
                    AND bi.book_id = r.book_id
                    AND bi.status = 'issued'
                )
                ORDER BY r.reservation_date
                """
            )
            rows = cur.fetchall()

    pickups = []
    for row in rows:
        pickups.append({
            "reservation_id": row[0],
            "student_name": row[1],
            "book_title": row[2],
            "reservation_date": row[3],
        })
    return pickups


def get_active_issues():
    """
    Returns every currently-issued (not yet returned) book, joined
    with student name, librarian name, and book title so the UI
    doesn't have to do separate lookups.
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT bi.issue_id, u.name, b.title, bi.issue_date, bi.due_date, lib.name
                FROM Book_Issue bi
                JOIN Users u ON bi.student_id = u.user_id
                JOIN Books b ON bi.book_id = b.book_id
                JOIN Users lib ON bi.librarian_id = lib.user_id
                WHERE bi.status = 'issued'
                ORDER BY bi.due_date
                """
            )
            rows = cur.fetchall()

    issues = []
    for row in rows:
        issues.append({
            "issue_id": row[0],
            "student_name": row[1],
            "book_title": row[2],
            "issue_date": row[3],
            "due_date": row[4],
            "librarian_name": row[5],
        })
    return issues