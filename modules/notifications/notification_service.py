"""
modules/notifications/notification_service.py

Finds who needs which kind of reminder, and sends them. Doesn't run
automatically on a schedule (see Phase 12 design discussion) -- this
is called from a "Send Reminders" button, so a librarian/admin
triggers it manually, e.g. once a day.
"""

import logging

from database import get_connection
from utils.email_utils import send_email, EmailConfigError

logger = logging.getLogger(__name__)


def get_due_tomorrow():
    """Active issues whose due_date is exactly tomorrow."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT u.name, u.email, b.title, bi.due_date
                FROM Book_Issue bi
                JOIN Users u ON bi.student_id = u.user_id
                JOIN Books b ON bi.book_id = b.book_id
                WHERE bi.status = 'issued'
                AND bi.due_date = CURRENT_DATE + 1
                """
            )
            rows = cur.fetchall()

    return [{"name": r[0], "email": r[1], "book_title": r[2], "due_date": r[3]} for r in rows]


def get_overdue():
    """Active issues whose due_date has already passed."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT u.name, u.email, b.title, bi.due_date
                FROM Book_Issue bi
                JOIN Users u ON bi.student_id = u.user_id
                JOIN Books b ON bi.book_id = b.book_id
                WHERE bi.status = 'issued'
                AND bi.due_date < CURRENT_DATE
                """
            )
            rows = cur.fetchall()

    return [{"name": r[0], "email": r[1], "book_title": r[2], "due_date": r[3]} for r in rows]


def get_reservations_ready_for_pickup():
    """
    Fulfilled reservations not yet collected -- Reservation.issue_id
    is still NULL (set by issue_reserved_book() once actually
    collected). Same logic as get_pending_pickups() in
    issue_service.py (Phase 9), duplicated here rather than imported
    to avoid a cross-module dependency for what's a fairly small
    query; both exist for a reason (one drives a UI table, this one
    drives emails).
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT u.name, u.email, b.title
                FROM Reservation r
                JOIN Users u ON r.student_id = u.user_id
                JOIN Books b ON r.book_id = b.book_id
                WHERE r.status = 'fulfilled' AND r.issue_id IS NULL
                """
            )
            rows = cur.fetchall()

    return [{"name": r[0], "email": r[1], "book_title": r[2]} for r in rows]


def send_all_reminders():
    """
    Sends every pending reminder (due tomorrow, overdue, reservation
    ready) in one go. Returns a summary dict so the UI can report
    back "sent 5, failed 1" instead of an all-or-nothing result --
    one bad email address shouldn't stop everyone else from getting
    theirs.
    """
    sent_count = 0
    failed_count = 0

    for issue in get_due_tomorrow():
        subject = f"Reminder: '{issue['book_title']}' is due tomorrow"
        body = (
            f"Hi {issue['name']},\n\n"
            f"This is a reminder that '{issue['book_title']}' is due back "
            f"tomorrow ({issue['due_date']}).\n\n"
            f"- Smart Digital Library"
        )
        if _try_send(issue["email"], subject, body):
            sent_count += 1
        else:
            failed_count += 1

    for issue in get_overdue():
        subject = f"Overdue: '{issue['book_title']}'"
        body = (
            f"Hi {issue['name']},\n\n"
            f"'{issue['book_title']}' was due back on {issue['due_date']} and "
            f"is now overdue. Please return it as soon as possible to avoid "
            f"further fines.\n\n"
            f"- Smart Digital Library"
        )
        if _try_send(issue["email"], subject, body):
            sent_count += 1
        else:
            failed_count += 1

    for reservation in get_reservations_ready_for_pickup():
        subject = f"'{reservation['book_title']}' is ready for pickup"
        body = (
            f"Hi {reservation['name']},\n\n"
            f"Good news -- '{reservation['book_title']}' that you reserved is "
            f"now available. Please visit the library to collect it.\n\n"
            f"- Smart Digital Library"
        )
        if _try_send(reservation["email"], subject, body):
            sent_count += 1
        else:
            failed_count += 1

    logger.info("Reminders sent: %s succeeded, %s failed", sent_count, failed_count)
    return {"sent": sent_count, "failed": failed_count}


def _try_send(to_email, subject, body):
    """
    Wraps send_email() so one failed email (bad address, network
    blip) doesn't crash the whole batch -- logs the failure and lets
    send_all_reminders() move on to the next recipient.
    """
    try:
        send_email(to_email, subject, body)
        return True
    except EmailConfigError:
        # credentials aren't set up at all -- no point retrying for
        # every single recipient, but we still let the caller know
        # via the failed count
        logger.error("Email not configured, skipping send to %s", to_email)
        return False
    except Exception:
        logger.exception("Failed to send email to %s", to_email)
        return False