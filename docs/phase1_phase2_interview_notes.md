# Smart Digital Library Management System — Phase 1 & 2 Deep Dive
### (Interview Preparation Notes)

---

## PHASE 1: DATABASE LAYER

### What you built (30-second interview answer)
"I designed and implemented the data layer for a desktop library management
system using PostgreSQL and Python. This included a normalized relational
schema with six tables, a connection-pooling layer instead of raw
per-query connections, and environment-based configuration so no
credentials are hardcoded."

### Why a connection pool instead of `psycopg2.connect()` every time?
- Opening a new TCP connection + PostgreSQL auth handshake on every query
  is slow and wasteful, especially in a desktop GUI where multiple widgets
  might hit the database in quick succession (search-as-you-type, dashboard
  widgets loading simultaneously).
- A pool (`psycopg2.pool.SimpleConnectionPool`) pre-opens a set of
  connections (min/max) and hands them out on demand, returning them to
  the pool when done — instead of destroying and recreating them.
- **Interview angle**: this shows you think about resource efficiency, not
  just "does it work."

### Why a context manager (`with get_connection() as conn`)?
- Guarantees the connection is returned to the pool **even if an exception
  is raised mid-query**. Without this pattern, a bug in business logic
  could silently leak connections until the pool is exhausted and the
  whole app stops working.
- This is the same principle as `with open(file) as f` in Python — resource
  acquisition/release tied to a scope, not manual bookkeeping.

### Why environment variables for config, not hardcoded credentials?
- Security: DB passwords should never be in source code / Git history.
- Portability: same code runs in dev, testing, and production by just
  changing environment variables — no code changes.
- Standard practice referenced as the "12-factor app" principle (store
  config in the environment).

### Key schema design decisions (know these cold)
| Decision | Why |
|---|---|
| PostgreSQL `ENUM` for `role`, `status` columns | Invalid values rejected at the **database** level, not just in app code — defense in depth |
| `CHECK (available_quantity <= total_quantity)` | Business rule enforced by the DB itself, so it can't be violated even by a future bug or a manual SQL script |
| Single `Users` table with a `role` column (not 3 separate tables) | Simpler foreign keys — `Book_Issue` and `Activity_Log` just reference "a person," regardless of role |
| Indexes on foreign key columns (`student_id`, `book_id`, etc.) | Postgres does NOT auto-index foreign keys (only primary keys) — without this, joins slow down as data grows |
| `TIMESTAMPTZ` instead of `TIMESTAMP` | Avoids silent bugs if the deployment server's timezone ever changes |
| Separate `schema.sql` file, not just inline Python DDL | Schema can be reviewed, versioned, and run independently (via psql/pgAdmin) — not buried inside application code |

### Common interviewer follow-ups (and how to answer)
- **"Why not use an ORM like SQLAlchemy?"**
  → "For this project I used raw SQL with psycopg2 to have full control
  over query performance and to deeply understand what's happening at the
  SQL level. An ORM would be a reasonable choice for a larger team project
  where developer velocity matters more than fine-grained control."
- **"What happens if two people issue the last copy of a book at the same time?"**
  → Honest answer: "Right now it's not handled with row-level locking —
  that's a race condition I'd want to fix with `SELECT ... FOR UPDATE`
  before this went to production. I designed the CHECK constraint so
  quantity can never go negative, but the second transaction would fail
  rather than being gracefully queued — that's an improvement I've noted."
  *(Interviewers respect honesty about known gaps far more than pretending everything's perfect.)*
- **"Why psycopg2 and not psycopg3?"**
  → "psycopg2 is the more battle-tested, widely-documented driver;
  psycopg3 is newer with async support I didn't need for a desktop app."

---

## PHASE 2: AUTHENTICATION

### What you built (30-second interview answer)
"I implemented the authentication layer — secure password hashing with
bcrypt, and a login service that verifies credentials against the
database using parameterized queries to prevent SQL injection. I also
made a deliberate security decision to use a single generic error
message so the system doesn't reveal whether an email is registered."

### Why bcrypt, not plain SHA-256 or storing plaintext?
- **Plaintext**: catastrophic if the database is ever breached — every
  user's real password is exposed immediately.
- **Fast hashes (SHA-256, MD5)**: wrong tool for passwords. They're
  *designed* to be fast, which is exactly what makes them vulnerable to
  brute-force and rainbow-table attacks — an attacker can try billions of
  guesses per second.
- **bcrypt**: deliberately slow (tunable "work factor" — I used 12
  rounds), which makes brute-forcing computationally expensive even if
  the password hashes leak. It also auto-generates a unique random salt
  per password, embedded in the hash itself — so no separate salt column
  is needed, and two users with the same password get completely
  different stored hashes.

### What is a "salt" and why does it matter? (classic interview question)
- A salt is random data mixed into the password before hashing.
- Without it: if two users pick the password "password123", their stored
  hashes would be identical — an attacker with a precomputed table of
  common password hashes ("rainbow table") could crack both instantly.
- With a unique salt per user: identical passwords produce completely
  different hashes, and precomputed tables become useless.

### Why parameterized queries instead of string formatting?
```python
# VULNERABLE — never do this:
cur.execute(f"SELECT * FROM Users WHERE email = '{email}'")

# SAFE — what I actually did:
cur.execute("SELECT * FROM Users WHERE email = %s", (email,))
```
- If `email` came from user input like `' OR '1'='1`, the vulnerable
  version would return every row in the table — a classic SQL injection
  bypassing authentication entirely.
- The parameterized version treats `email` strictly as **data**, never as
  part of the SQL command — psycopg2 handles escaping internally.
- **This is one of the highest-value things to say in an interview** —
  SQL injection is consistently one of the most common real-world
  vulnerabilities (OWASP Top 10), and being able to explain *why* the
  fix works (not just that you used it) stands out.

### Why one generic error ("Invalid email or password") instead of
### specific errors ("no such user" vs "wrong password")?
- If the system says "no such user" for unregistered emails and something
  else for wrong passwords, an attacker can silently enumerate which
  emails have accounts on the system — a real privacy/security leak, even
  without cracking any password.
- Returning identical messages for both cases closes that side channel.

### Why is the `CurrentUser` object immutable (`frozen=True` dataclass)?
- Once someone logs in, nothing downstream should be able to silently
  mutate their session — e.g., accidentally (or maliciously) changing
  `.role` from `student` to `admin` in memory. Immutability forces any
  role change to go through the actual database, where it's
  auditable and validated.

### Common interviewer follow-ups
- **"How would you add rate-limiting / prevent brute force login attempts?"**
  → "I'd track failed attempts per email or IP, with either a temporary
  lockout after N failures, or exponential backoff. I logged failed
  attempts to an Activity_Log table already, which is a foundation for
  that — the next step would be querying that log to detect and block
  rapid repeated failures."
- **"How do you handle password reset?"**
  → "Not built yet — I'd implement a time-limited, single-use token sent
  via email, never emailing the actual password (since we don't even
  store it in reversible form to begin with)."
- **"What's the difference between hashing and encryption?"**
  → "Encryption is reversible (you can decrypt it back with a key) —
  used when you need to recover the original data. Hashing is
  one-directional — you never need to recover the original password,
  only verify a match, so hashing is the correct tool here."

---

## HOW TO ACTUALLY UNDERSTAND THIS (NOT JUST MEMORIZE)

Reading these notes will let you *talk* about the project, but real
understanding — the kind that survives a follow-up question you didn't
prepare for — comes from doing these four things:

### 1. Re-read your own code line by line and ask "why," not "what"
Anyone can read `bcrypt.hashpw(...)` and know it hashes a password. The
interview-winning move is being able to answer "why 12 rounds and not
4 or 20?" (tradeoff between security and login speed) or "why does
`verify_password` never raise an exception?" (so the UI layer has one
simple code path). Go back through `password_utils.py`, `auth_service.py`,
`database.py`, and for every line, ask "what would break if I removed
this line, or did it differently?"

### 2. Break things on purpose, locally
You already did some of this by accident (the password env var bug, the
`databse` typo) — that's exactly how real understanding forms. Now do it
deliberately:
- Temporarily change `%s` to an f-string in `auth_service.py`, then try
  logging in with an email like `' OR '1'='1' --` and watch what happens
  (in a throwaway test DB only). Seeing the actual injection succeed
  teaches you more than any explanation.
- Remove the `CHECK (available_quantity <= total_quantity)` constraint
  temporarily and try to make quantity negative — see what breaks.
- Comment out `conn.rollback()` in the context manager and force an
  error mid-transaction — see the DB end up in an inconsistent state.

### 3. Explain each phase out loud, to yourself or a friend, with zero notes
If you get stuck explaining *why* you made a choice (not just *what* you
did), that's exactly the gap to go re-study. Recording yourself and
listening back is uncomfortable but extremely effective.

### 4. Connect each decision to a *general* software engineering principle
Interviewers care less about "I used bcrypt" and more about whether you
understand the underlying principle, because that transfers to any
future stack:
- Connection pooling → **resource management / reuse over recreation**
- Context managers → **RAII-style resource safety** (acquire → guaranteed release)
- Parameterized queries → **never trust user input; separate code from data**
- Generic error messages → **don't leak information through side channels**
- CHECK constraints in the DB → **defense in depth — validate at every layer, not just one**
- Environment-based config → **separate configuration from code**

If you can explain each phase both at the "what I built" level and the
"what general principle this demonstrates" level, you're ready for
almost any follow-up question an interviewer throws at you.