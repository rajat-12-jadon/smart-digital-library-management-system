"""
modules/fine/fine_service.py

Fine records are already CREATED elsewhere -- return_book() in
issue_service.py (Phase 8) inserts a Fine row automatically when a
book comes back late. This module is just for VIEWING and managing
those existing records: librarians see pending fines and mark them
paid, students see their own fine history.
"""

import logging

from database import get_connection

logger = logging.getLogger(__name__)


def get_pending_fines():
    """
    Returns every unpaid fine, joined with student name and book
    title, for the librarian's "collect fines" screen.
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT f.fine_id, u.name, b.title, f.late_days, f.fine_amount
                FROM Fine f
                JOIN Book_Issue bi ON f.issue_id = bi.issue_id
                JOIN Users u ON bi.student_id = u.user_id
                JOIN Books b ON bi.book_id = b.book_id
                WHERE f.paid = FALSE
                ORDER BY f.fine_id
                """
            )
            rows = cur.fetchall()

    fines = []
    for row in rows:
        fines.append({
            "fine_id": row[0],
            "student_name": row[1],
            "book_title": row[2],
            "late_days": row[3],
            "fine_amount": row[4],
        })
    return fines


def get_fines_for_student(student_id):
    """
    Returns a student's own fines (paid AND unpaid, so they can see
    their history, not just what they currently owe), with book title.
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT f.fine_id, b.title, f.late_days, f.fine_amount, f.paid
                FROM Fine f
                JOIN Book_Issue bi ON f.issue_id = bi.issue_id
                JOIN Books b ON bi.book_id = b.book_id
                WHERE bi.student_id = %s
                ORDER BY f.fine_id DESC
                """,
                (student_id,),
            )
            rows = cur.fetchall()

    fines = []
    for row in rows:
        fines.append({
            "fine_id": row[0],
            "book_title": row[1],
            "late_days": row[2],
            "fine_amount": row[3],
            "paid": row[4],
        })
    return fines


def mark_fine_paid(fine_id):
    """Marks a fine as paid. No quantity/availability side effects -- just a status flip."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE Fine SET paid = TRUE WHERE fine_id = %s AND paid = FALSE",
                (fine_id,),
            )
            if cur.rowcount == 0:
                raise ValueError("Fine not found, or it's already marked as paid.")
        conn.commit()

    logger.info("Fine marked paid: fine_id=%s", fine_id)