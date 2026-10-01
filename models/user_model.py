"""User data-access layer.

Wraps raw SQL access to the `users` table behind a small repository
class, with module-level function wrappers exposing the stable,
spec-mandated call surface used by `routes/auth_routes.py` and any other
caller: `create_user`, `get_user_by_email`, `get_user_by_id`.
"""
import logging

import pymysql

from db import execute, query_one

logger = logging.getLogger(__name__)


class UserRepository:
    """Encapsulates all SQL statements touching the `users` table."""

    def create(self, name: str, email: str, password_hash: str, role: str) -> int:
        """Insert a new user and return its id.

        Raises:
            ValueError: if a user with this email already exists.
        """
        existing = self.find_by_email(email)
        if existing is not None:
            raise ValueError(f"Email already registered: {email}")

        try:
            user_id = execute(
                "INSERT INTO users (name, email, password_hash, role) "
                "VALUES (%s, %s, %s, %s)",
                (name, email, password_hash, role),
            )
        except pymysql.err.IntegrityError as exc:
            # Defends against a race between the pre-check above and the
            # insert (unique constraint on email is the final guard).
            raise ValueError(f"Email already registered: {email}") from exc

        logger.info("User created: id=%s role=%s", user_id, role)
        return user_id

    def find_by_email(self, email: str) -> dict | None:
        return query_one("SELECT * FROM users WHERE email = %s", (email,))

    def find_by_id(self, user_id: int) -> dict | None:
        return query_one("SELECT * FROM users WHERE id = %s", (user_id,))


_user_repository = UserRepository()


def create_user(name: str, email: str, password_hash: str, role: str) -> int:
    """Create a user, returning the new user id.

    Raises ValueError if the email is already registered.
    """
    return _user_repository.create(name, email, password_hash, role)


def get_user_by_email(email: str) -> dict | None:
    """Return the user dict for the given email, or None if not found."""
    return _user_repository.find_by_email(email)


def get_user_by_id(user_id: int) -> dict | None:
    """Return the user dict for the given id, or None if not found."""
    return _user_repository.find_by_id(user_id)
