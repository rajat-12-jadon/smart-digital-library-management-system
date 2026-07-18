"""
tests/test_issue_return.py

Tests for modules/issue_return/issue_service.py -- covers the atomic
transaction logic from Phase 7/8 (the highest-value code to test,
since it's the most complex business logic in the project).
"""

import pytest
from datetime import date, timedelta

from modules.issue_return.issue_service import (
    issue_book, return_book, _calculate_fine,
)
from database import get_connection
from tests.helpers import create_user, create_book


@pytest.fixture
def student_id():
    return create_user("Test Student", "student@test.com", "Password123", "student")


@pytest.fixture
def librarian_id():
    return create_user("Test Librarian", "librarian@test.com", "Password123", "librarian")


def test_issue_book_reduces_available_quantity(student_id, librarian_id):
    book_id = create_book("Test Book", total_quantity=3)

    issue_book(student_id, librarian_id, book_id)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT available_quantity FROM Books WHERE book_id = %s", (book_id,))
            available = cur.fetchone()[0]

    assert available == 2  # started at 3, one issued


def test_issue_book_rejects_when_no_copies_available(student_id, librarian_id):
    book_id = create_book("Test Book", total_quantity=1)

    issue_book(student_id, librarian_id, book_id)  # takes the only copy

    another_student = create_user("Another Student", "student2@test.com", "Password123", "student")

    with pytest.raises(ValueError):
        issue_book(another_student, librarian_id, book_id)


def test_issue_book_rejects_duplicate_issue_to_same_student(student_id, librarian_id):
    book_id = create_book("Test Book", total_quantity=5)

    issue_book(student_id, librarian_id, book_id)

    with pytest.raises(ValueError):
        issue_book(student_id, librarian_id, book_id)


def test_return_book_increases_available_quantity(student_id, librarian_id):
    book_id = create_book("Test Book", total_quantity=3)

    issue_id, _ = issue_book(student_id, librarian_id, book_id)
    return_book(issue_id)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT available_quantity FROM Books WHERE book_id = %s", (book_id,))
            available = cur.fetchone()[0]

    assert available == 3  # back to full


def test_return_book_rejects_already_returned_issue(student_id, librarian_id):
    book_id = create_book("Test Book", total_quantity=3)

    issue_id, _ = issue_book(student_id, librarian_id, book_id)
    return_book(issue_id)  # first return succeeds

    with pytest.raises(ValueError):
        return_book(issue_id)  # second return on the same issue should fail


def test_return_book_on_time_creates_no_fine(student_id, librarian_id):
    book_id = create_book("Test Book", total_quantity=3)

    issue_id, _ = issue_book(student_id, librarian_id, book_id)
    late_days, fine_amount, _ = return_book(issue_id)

    assert late_days == 0
    assert fine_amount is None


def test_return_book_late_creates_correct_fine(student_id, librarian_id):
    """
    issue_book() always sets due_date 14 days out, so we can't easily
    make it "already overdue" through the public function. Instead we
    manually backdate the due_date afterward (same trick as
    create_test_overdue_issue.py) to simulate a late return.
    """
    book_id = create_book("Test Book", total_quantity=3)
    issue_id, _ = issue_book(student_id, librarian_id, book_id)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE Book_Issue SET due_date = %s WHERE issue_id = %s",
                (date.today() - timedelta(days=6), issue_id),
            )
        conn.commit()

    late_days, fine_amount, _ = return_book(issue_id)

    assert late_days == 6
    assert fine_amount == 60  # 6 days in the 4-7 day slab, Rs 10/day


@pytest.mark.parametrize("late_days,expected_fine", [
    (1, 5),      # 1-3 day slab: Rs 5/day
    (3, 15),
    (4, 40),     # 4-7 day slab: Rs 10/day
    (7, 70),
    (8, 160),    # 8-15 day slab: Rs 20/day
    (15, 300),
    (16, 800),   # 16+ slab: Rs 50/day
    (20, 1000),
])
def test_calculate_fine_matches_expected_slab(late_days, expected_fine):
    """
    Directly tests the fine slab logic from config.FINE_RULES, without
    needing to issue/return a real book for every case.
    @pytest.mark.parametrize runs this same test once per tuple in the
    list -- 8 separate test cases from one function body, instead of
    copy-pasting the same assertion 8 times with different numbers.
    """
    assert _calculate_fine(late_days) == expected_fine