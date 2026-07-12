"""
seed_admin.py

Standalone utility to create a test Admin user, so we can verify the
login flow (auth_service.login) end-to-end before the UI exists.

NOT part of the app itself and NOT the real registration flow --
Phase 3 (Dashboards) will build proper Admin/Librarian/Student
registration through the UI. This is a throwaway dev convenience.

Idempotent: safe to run more than once. If the email already exists,
it reports that instead of crashing on a duplicate-key error.
"""

from database import init_pool, get_connection, close_pool
from auth.password_utils import hash_password

# Change these if you want a different test login
TEST_ADMIN_NAME = "Rajat Jadon"
TEST_ADMIN_EMAIL = "admin@test.com"
TEST_ADMIN_PASSWORD = "Admin@123"


def seed_admin():
    init_pool()

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT user_id FROM Users WHERE email = %s",
                (TEST_ADMIN_EMAIL,),
            )
            existing = cur.fetchone()

            if existing:
                print(f"Admin user already exists (user_id={existing[0]}). Skipping.")
                close_pool()
                return

            hashed = hash_password(TEST_ADMIN_PASSWORD)

            cur.execute(
                """
                INSERT INTO Users (name, email, password, role)
                VALUES (%s, %s, %s, 'admin')
                RETURNING user_id
                """,
                (TEST_ADMIN_NAME, TEST_ADMIN_EMAIL, hashed),
            )
            new_id = cur.fetchone()[0]
        conn.commit()

    print(f"Test admin created: user_id={new_id}, email={TEST_ADMIN_EMAIL}")
    print(f"Login with email='{TEST_ADMIN_EMAIL}' password='{TEST_ADMIN_PASSWORD}'")

    close_pool()


if __name__ == "__main__":
    seed_admin()