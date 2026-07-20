"""
create_test_overdue_issue.py

Dev-only utility -- creates a Book_Issue record with a due_date in the
past, so you can test fine calculation (return_book() in
issue_service.py) without waiting for a real book to actually become
overdue. Not part of the real app.

Usage: just edit the three values below and run it.
"""

from database import init_pool, get_connection, close_pool

# ---- edit these before running ----
STUDENT_EMAIL = "aman@test.com"     # must be an existing student
LIBRARIAN_EMAIL = "librarian@test.com"  # must be an existing librarian
BOOK_TITLE = "Harry Potter"          # must be an existing book (exact title)
DAYS_OVERDUE = 6                     # how many days past the due date
# ------------------------------------


def create_test_overdue_issue():
    init_pool()

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT user_id FROM Users WHERE email = %s AND role = 'student'",
                (STUDENT_EMAIL,),
            )
            student_row = cur.fetchone()
            if student_row is None:
                print(f"No student found with email '{STUDENT_EMAIL}'.")
                close_pool()
                return
            student_id = student_row[0]

            cur.execute(
                "SELECT user_id FROM Users WHERE email = %s AND role = 'librarian'",
                (LIBRARIAN_EMAIL,),
            )
            librarian_row = cur.fetchone()
            if librarian_row is None:
                print(f"No librarian found with email '{LIBRARIAN_EMAIL}'.")
                close_pool()
                return
            librarian_id = librarian_row[0]

            cur.execute(
                "SELECT book_id FROM Books WHERE title = %s",
                (BOOK_TITLE,),
            )
            book_row = cur.fetchone()
            if book_row is None:
                print(f"No book found with title '{BOOK_TITLE}'.")
                close_pool()
                return
            book_id = book_row[0]

            # BUG FIX: this script previously inserted a Book_Issue row
            # directly without reducing available_quantity, unlike the
            # real issue_book() function. That desynced the book's
            # quantity from reality -- returning this fake issue later
            # would try to push available_quantity above total_quantity,
            # violating the available_not_exceed_total CHECK constraint
            # and crashing. Fixed by mirroring what issue_book() does:
            # check availability first, then decrement it here too.
            cur.execute(
                "SELECT available_quantity FROM Books WHERE book_id = %s FOR UPDATE",
                (book_id,),
            )
            available = cur.fetchone()[0]
            if available <= 0:
                print(f"'{BOOK_TITLE}' has no available copies -- can't create a test issue for it.")
                close_pool()
                return

            # issue_date is set further back than due_date so the
            # numbers stay realistic (14 day loan period + how overdue
            # it is), though nothing actually checks issue_date's
            # relationship to due_date -- it's just for a sane-looking
            # record. Postgres supports `date - integer` directly (each
            # integer = 1 day subtracted), which is simpler and safer
            # to parameterize than an INTERVAL string literal.
            cur.execute(
                """
                INSERT INTO Book_Issue
                    (student_id, librarian_id, book_id, issue_date, due_date, status)
                VALUES (
                    %s, %s, %s,
                    CURRENT_DATE - %s,
                    CURRENT_DATE - %s,
                    'issued'
                )
                RETURNING issue_id
                """,
                (student_id, librarian_id, book_id, 14 + DAYS_OVERDUE, DAYS_OVERDUE),
            )
            new_issue_id = cur.fetchone()[0]

            cur.execute(
                "UPDATE Books SET available_quantity = available_quantity - 1 WHERE book_id = %s",
                (book_id,),
            )
        conn.commit()

    print(f"Test overdue issue created: issue_id={new_issue_id}")
    print(f"  Student: {STUDENT_EMAIL}")
    print(f"  Book: {BOOK_TITLE}")
    print(f"  {DAYS_OVERDUE} days overdue -- return it in the Issue Book screen to test the fine.")

    close_pool()


if __name__ == "__main__":
    create_test_overdue_issue()