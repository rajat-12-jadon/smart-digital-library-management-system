"""
tests/conftest.py

pytest automatically finds and loads this file before running any
tests -- it's the standard place for shared setup ("fixtures") that
multiple test files need.

The most important thing here: we redirect the app's database
connection to a SEPARATE test database (library_management_system_test)
before any test runs, so tests can freely create/delete data without
ever touching your real data.
"""

import pytest

import config

# IMPORTANT: this line must run BEFORE `from database import ...` below.
# config.DB_CONFIG is a dict, and `database.py` does
# `from config import DB_CONFIG` -- that import creates a reference to
# the SAME dict object in memory, not a copy. So mutating one key here
# (dbname) changes what database.py sees too, without needing to
# touch database.py itself at all.
config.DB_CONFIG["dbname"] = "library_management_system_test"

from database import init_pool, close_pool, get_connection


@pytest.fixture(scope="session", autouse=True)
def _test_database_pool():
    """
    Runs ONCE for the entire test session (scope="session"), not once
    per test. autouse=True means every test gets this automatically --
    no test file needs to explicitly ask for it.
    """
    init_pool()
    yield  # tests run here
    close_pool()


@pytest.fixture(autouse=True)
def _clean_tables():
    """
    Runs before AND after every single test (autouse=True, no
    scope specified = default "function" scope, meaning per-test).
    Wipes every table so each test starts from a known-empty state
    and doesn't see leftover data from a previous test.

    TRUNCATE ... RESTART IDENTITY CASCADE:
    - TRUNCATE is faster than DELETE for wiping a whole table
    - RESTART IDENTITY resets SERIAL counters back to 1 (so
      user_id/book_id in each test are predictable)
    - CASCADE also truncates any table with a foreign key pointing
      at these (skips having to list every dependent table manually,
      and avoids foreign-key-violation errors from truncating in the
      wrong order)
    """
    _wipe_all_tables()
    yield  # the actual test runs here
    _wipe_all_tables()


def _wipe_all_tables():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "TRUNCATE Fine, Reservation, Book_Issue, Books, Activity_Log, Users "
                "RESTART IDENTITY CASCADE"
            )
        conn.commit()