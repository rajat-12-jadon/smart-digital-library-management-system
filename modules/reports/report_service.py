"""
modules/reports/report_service.py

All six reports from the original project spec. Each function returns
a list of dicts (or a single summary dict for pending fines) -- same
pattern as every other service module, so report_ui.py can display
results without caring about SQL details.

None of these queries modify anything -- they're all read-only
aggregations over existing data (Book_Issue, Books, Users, Fine).
"""

import logging

from database import get_connection

logger = logging.getLogger(__name__)


def get_most_issued_books(limit=10):
    """Books ordered by how many times they've been issued, most first."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT b.title, b.author, COUNT(bi.issue_id) AS issue_count
                FROM Books b
                JOIN Book_Issue bi ON b.book_id = bi.book_id
                GROUP BY b.book_id, b.title, b.author
                ORDER BY issue_count DESC
                LIMIT %s
                """,
                (limit,),
            )
            rows = cur.fetchall()

    return [{"title": r[0], "author": r[1], "issue_count": r[2]} for r in rows]


def get_least_issued_books(limit=10):
    """
    Books ordered by how many times they've been issued, least first.
    Uses a LEFT JOIN (not the INNER JOIN that get_most_issued_books
    uses) so books with ZERO issues still show up with a count of 0 --
    an INNER JOIN would silently exclude books that have never been
    issued at all, which is exactly the information this report needs
    to surface.
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT b.title, b.author, COUNT(bi.issue_id) AS issue_count
                FROM Books b
                LEFT JOIN Book_Issue bi ON b.book_id = bi.book_id
                GROUP BY b.book_id, b.title, b.author
                ORDER BY issue_count ASC
                LIMIT %s
                """,
                (limit,),
            )
            rows = cur.fetchall()

    return [{"title": r[0], "author": r[1], "issue_count": r[2]} for r in rows]


def get_top_readers(limit=10):
    """Students ordered by how many books they've issued, most first."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT u.name, u.email, COUNT(bi.issue_id) AS books_issued
                FROM Users u
                JOIN Book_Issue bi ON u.user_id = bi.student_id
                WHERE u.role = 'student'
                GROUP BY u.user_id, u.name, u.email
                ORDER BY books_issued DESC
                LIMIT %s
                """,
                (limit,),
            )
            rows = cur.fetchall()

    return [{"name": r[0], "email": r[1], "books_issued": r[2]} for r in rows]


def get_pending_fine_summary():
    """
    Total unpaid fine amount and count, across the whole system --
    a quick top-level number for the admin, not a per-fine list
    (that's what Manage Fines, from Phase 10, already shows).
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(*), COALESCE(SUM(fine_amount), 0)
                FROM Fine
                WHERE paid = FALSE
                """
            )
            row = cur.fetchone()

    return {"pending_count": row[0], "pending_total": row[1]}


def get_monthly_issue_count():
    """
    Number of books issued per calendar month, most recent month
    first. DATE_TRUNC('month', issue_date) rounds every date down to
    the 1st of its month, so grouping by that groups all issues within
    the same month together regardless of the exact day.
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT DATE_TRUNC('month', issue_date) AS month, COUNT(*) AS issue_count
                FROM Book_Issue
                GROUP BY month
                ORDER BY month DESC
                """
            )
            rows = cur.fetchall()

    return [{"month": r[0].strftime("%B %Y"), "issue_count": r[1]} for r in rows]


def get_monthly_return_count():
    """
    Same idea as get_monthly_issue_count(), but grouped by return_date
    instead. WHERE return_date IS NOT NULL excludes books that are
    still currently issued (their return_date is NULL until returned).
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT DATE_TRUNC('month', return_date) AS month, COUNT(*) AS return_count
                FROM Book_Issue
                WHERE return_date IS NOT NULL
                GROUP BY month
                ORDER BY month DESC
                """
            )
            rows = cur.fetchall()

    return [{"month": r[0].strftime("%B %Y"), "return_count": r[1]} for r in rows]