"""
database.py

Single source of truth for PostgreSQL connectivity.

Design choice: we use a connection POOL (psycopg2.pool.SimpleConnectionPool)
rather than opening a fresh connection per query. In a desktop Tkinter app,
many parts of the UI may need DB access in quick succession (dashboard
widgets, search-as-you-type, etc.) — a pool avoids the overhead of
repeatedly establishing TCP + auth handshakes with PostgreSQL, and protects
us from accidentally leaking unclosed connections.

Every other module MUST go through get_connection() and MUST use it as a
context manager, so connections are always returned to the pool even if
an exception occurs mid-query.
"""

import logging
from contextlib import contextmanager

import psycopg2
from psycopg2 import pool as pg_pool

from config import DB_CONFIG

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

_connection_pool = None


def init_pool(minconn: int = 1, maxconn: int = 10) -> None:
    """
    Initialize the global connection pool. Called once at application
    startup (main.py). Kept separate from module import time so that
    a failed DB connection doesn't crash the app the instant any
    module is imported -- we want a controlled, user-facing error
    instead (e.g. a "cannot connect to database" splash screen).
    """
    global _connection_pool

    if _connection_pool is not None:
        logger.info("Connection pool already initialized.")
        return

    try:
        _connection_pool = pg_pool.SimpleConnectionPool(
            minconn,
            maxconn,
            host=DB_CONFIG["host"],
            port=DB_CONFIG["port"],
            dbname=DB_CONFIG["dbname"],
            user=DB_CONFIG["user"],
            password=DB_CONFIG["password"],
        )
        logger.info("Database connection pool initialized successfully.")
    except psycopg2.OperationalError as e:
        logger.error("Failed to initialize database connection pool: %s", e)
        raise


@contextmanager
def get_connection():
    """
    Context manager that hands out a connection from the pool and
    guarantees it's returned afterward -- even on exception.

    Usage:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1;")
                result = cur.fetchone()

    We deliberately do NOT auto-commit here. Commit/rollback is the
    caller's responsibility (business logic layer), because only the
    caller knows whether a multi-statement operation succeeded as a
    whole (e.g. "reduce book quantity" + "insert issue record" must
    commit together or not at all).
    """
    if _connection_pool is None:
        raise RuntimeError(
            "Connection pool not initialized. Call init_pool() at app startup."
        )

    conn = _connection_pool.getconn()
    try:
        yield conn
    except Exception:
        conn.rollback()
        raise
    finally:
        _connection_pool.putconn(conn)


def close_pool() -> None:
    """Close all connections in the pool. Called on application shutdown."""
    global _connection_pool
    if _connection_pool is not None:
        _connection_pool.closeall()
        _connection_pool = None
        logger.info("Database connection pool closed.")