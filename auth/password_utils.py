"""
auth/password_utils.py

Wraps bcrypt so no other module ever imports bcrypt directly or reasons
about salts/work factors. If we ever need to change the hashing scheme
(e.g. tune the work factor, or migrate algorithms), this is the only
file that changes.

Why bcrypt over hashlib.sha256 etc:
- bcrypt has a built-in, per-hash random salt (no separate salt column
  needed in the Users table)
- bcrypt is deliberately slow (tunable work factor) which makes brute
  force / rainbow table attacks impractical -- a fast hash like SHA-256
  is the wrong tool for passwords even though it's fine for checksums.
"""

import bcrypt

# Work factor: higher = slower to hash = more brute-force resistant,
# but also slower for legitimate logins. 12 is a reasonable default
# for a desktop app in 2026 hardware; revisit if login feels slow.
_WORK_FACTOR = 12


def hash_password(plain_password: str) -> str:
    """
    Hash a plaintext password for storage. Returns a string safe to
    store directly in Users.password (bcrypt output is ASCII).
    """
    if not plain_password:
        raise ValueError("Password cannot be empty.")

    salt = bcrypt.gensalt(rounds=_WORK_FACTOR)
    hashed = bcrypt.hashpw(plain_password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, stored_hash: str) -> bool:
    """
    Check a login attempt's plaintext password against the stored hash.
    Returns False (never raises) on malformed input, so callers can
    treat "invalid" and "error" the same way -- a login form doesn't
    need to distinguish "corrupt hash" from "wrong password".
    """
    if not plain_password or not stored_hash:
        return False

    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"), stored_hash.encode("utf-8")
        )
    except (ValueError, TypeError):
        return False