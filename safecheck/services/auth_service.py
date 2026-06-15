"""Authentication service — login and user lookup."""
from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from safecheck.core import models
from safecheck.core.security import verify_password


def authenticate(session: Session, identifier: str, password: str) -> models.User | None:
    """Return the matching active user for *identifier* + *password*, else None.

    *identifier* may be either a username or an email address.
    """
    identifier = (identifier or "").strip()
    if not identifier or not password:
        return None

    user = session.scalars(
        select(models.User).where(
            or_(models.User.username == identifier, models.User.email == identifier)
        )
    ).first()

    if user is None or not user.is_active:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def get_user(session: Session, user_id: int) -> models.User | None:
    """Fetch a user by primary key."""
    return session.get(models.User, user_id)
