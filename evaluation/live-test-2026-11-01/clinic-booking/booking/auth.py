"""Staff authentication.

Passwords are hashed with scrypt (see docs/decisions/0002-hash-staff-passwords-with-scrypt.md).
Legacy unsalted SHA-256 hashes still verify and are upgraded after the next successful sign-in.
"""

import functools
import hashlib
import hmac
import os
from typing import Dict, Optional

# OWASP's documented minimum for scrypt; see docs/research/2026-11-01-password-hashing.md.
SCRYPT_N = 2 ** 17
SCRYPT_R = 8
SCRYPT_P = 1
# scrypt needs about 128 * N * r bytes (128 MiB at these settings); OpenSSL's default limit is lower.
SCRYPT_MAXMEM = 256 * 1024 * 1024
# Upper bound accepted from stored hashes, so a tampered record cannot demand unbounded memory.
MAX_STORED_N = 2 ** 20
SALT_BYTES = 16
KEY_BYTES = 32
PREFIX = "scrypt"


def hash_password(password: str, n: Optional[int] = None, r: Optional[int] = None, p: Optional[int] = None) -> str:
    n, r, p = n or SCRYPT_N, r or SCRYPT_R, p or SCRYPT_P
    salt = os.urandom(SALT_BYTES)
    key = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=n, r=r, p=p, maxmem=SCRYPT_MAXMEM, dklen=KEY_BYTES)
    return f"{PREFIX}${n}${r}${p}${salt.hex()}${key.hex()}"


def _is_legacy(stored_hash: str) -> bool:
    return len(stored_hash) == 64 and all(char in "0123456789abcdef" for char in stored_hash)


def _parse(stored_hash: str):
    parts = stored_hash.split("$")
    if len(parts) != 6 or parts[0] != PREFIX:
        raise ValueError("not a scrypt hash")
    n, r, p = int(parts[1]), int(parts[2]), int(parts[3])
    if not (1 < n <= MAX_STORED_N and 0 < r <= 32 and 0 < p <= 16):
        raise ValueError("scrypt parameters out of range")
    return n, r, p, bytes.fromhex(parts[4]), bytes.fromhex(parts[5])


def verify_password(password: str, stored_hash: str) -> bool:
    """Check a password against a stored hash. Unknown or malformed formats fail closed."""
    if _is_legacy(stored_hash):
        candidate = hashlib.sha256(password.encode("utf-8")).hexdigest()
        return hmac.compare_digest(candidate, stored_hash)
    try:
        n, r, p, salt, key = _parse(stored_hash)
    except ValueError:
        return False
    candidate = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=n, r=r, p=p, maxmem=SCRYPT_MAXMEM,
                               dklen=len(key))
    return hmac.compare_digest(candidate, key)


def needs_rehash(stored_hash: str) -> bool:
    if _is_legacy(stored_hash):
        return True
    try:
        n, r, p, _, _ = _parse(stored_hash)
    except ValueError:
        return True
    return (n, r, p) != (SCRYPT_N, SCRYPT_R, SCRYPT_P)


@functools.lru_cache(maxsize=1)
def _dummy_hash() -> str:
    """A hash checked for unknown usernames, so response time does not reveal which usernames exist."""
    return hash_password(os.urandom(16).hex())


class StaffDirectory:
    """Staff accounts: username to password hash."""

    def __init__(self) -> None:
        self._hashes: Dict[str, str] = {}

    def add(self, username: str, password: str) -> None:
        self._hashes[username] = hash_password(password)

    def authenticate(self, username: str, password: str) -> bool:
        stored = self._hashes.get(username)
        if stored is None:
            verify_password(password, _dummy_hash())
            return False
        if not verify_password(password, stored):
            return False
        if needs_rehash(stored):
            self._hashes[username] = hash_password(password)
        return True
