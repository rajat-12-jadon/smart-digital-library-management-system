"""
seed_librarian.py

Same idea as seed_admin.py -- creates a test librarian account so we
can log in and test the Student Module. Not part of the real app,
just a dev convenience until Phase 6 (real "Add Librarian" UI) exists.
"""

from database import init_pool, get_connection, close_pool
from auth.password_utils import hash_password

TEST_LIBRARIAN_NAME = "Priya Sharma"
TEST_LIBRARIAN_EMAIL = "librarian@test.com"
TEST_LIBRARIAN_PASSWORD = "Librarian@123"


def seed_librarian():
    init_pool()

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT user_id FROM Users WHERE email = %s",
                (TEST_LIBRARIAN_EMAIL,),
            )
            existing = cur.fetchone()

            if existing:
                print(f"Librarian already exists (user_id={existing[0]}). Skipping.")
                close_pool()
                return

            hashed = hash_password(TEST_LIBRARIAN_PASSWORD)

            cur.execute(
                """
                INSERT INTO Users (name, email, password, role)
                VALUES (%s, %s, %s, 'librarian')
                RETURNING user_id
                """,
                (TEST_LIBRARIAN_NAME, TEST_LIBRARIAN_EMAIL, hashed),
            )
            new_id = cur.fetchone()[0]
        conn.commit()

    print(f"Test librarian created: user_id={new_id}, email={TEST_LIBRARIAN_EMAIL}")
    print(f"Login with email='{TEST_LIBRARIAN_EMAIL}' password='{TEST_LIBRARIAN_PASSWORD}'")

    close_pool()


if __name__ == "__main__":
    seed_librarian()