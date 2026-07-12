"""
test_connection.py

Standalone sanity check -- run this once after setup to confirm the
database connection layer works before building anything on top of it.
Not part of the formal test suite (that comes in Phase 14); this is a
throwaway manual check.
"""

from database import init_pool, get_connection, close_pool

def main():
    print("Initializing connection pool...")
    init_pool()

    print("Requesting a connection and running a test query...")
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT version();")
            version = cur.fetchone()[0]
            print("Connected successfully.")
            print("PostgreSQL version:", version)

            cur.execute("""
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name;
            """)
            tables = [row[0] for row in cur.fetchall()]
            print("Tables found:", tables)

    close_pool()
    print("Pool closed. Setup verified.")

if __name__ == "__main__":
    main()