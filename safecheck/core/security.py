"""Password hashing helpers built on Passlib + Bcrypt.

The rest of the application never touches raw passwords beyond passing them
through :func:`hash_password` and :func:`verify_password`.
"""
from __future__ import annotations

from passlib.context import CryptContext

# A single shared context. Bcrypt is the spec-mandated hashing scheme.
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    """Return a salted bcrypt hash for *plain_password*."""
    return _pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Check *plain_password* against a stored bcrypt *hashed_password*."""
    try:
        return _pwd_context.verify(plain_password, hashed_password)
    except ValueError:
        # Malformed or empty hash — treat as a failed verification.
        return False
