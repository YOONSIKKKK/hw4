"""Password hashing for Campus Customs accounts.

Matches the scheme the seeded accounts already use, so the shipped test
account keeps working: PBKDF2-HMAC-SHA256 over a per-user random salt,
stored as `pbkdf2_sha256$<salt>$<hex digest>`. Plaintext passwords are
never stored, logged, or returned.
"""

import hashlib
import hmac
import secrets

ALGORITHM = "pbkdf2_sha256"
ITERATIONS = 120_000
SALT_BYTES = 8


def _derive(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), ITERATIONS
    ).hex()


def hash_password(password: str) -> str:
    salt = secrets.token_hex(SALT_BYTES)
    return f"{ALGORITHM}${salt}${_derive(password, salt)}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algorithm, salt, digest = stored.split("$")
    except ValueError:
        return False
    if algorithm != ALGORITHM:
        return False
    return hmac.compare_digest(_derive(password, salt), digest)
