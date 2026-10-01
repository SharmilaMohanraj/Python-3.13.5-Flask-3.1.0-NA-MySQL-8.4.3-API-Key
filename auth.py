"""JWT and password utilities, plus the two auth decorators every
protected route uses.

Classes own the actual hashing/token mechanics (single responsibility,
easy to unit test in isolation); the module-level functions are the
stable, spec-mandated call surface (`hash_password`, `verify_password`,
`generate_token`, `decode_token`) that the rest of the app imports.
"""
import logging
from datetime import datetime, timedelta, timezone
from functools import wraps

import bcrypt
import jwt
from flask import g, request

from config import config
from errors import AuthenticationError, UnauthorizedError

logger = logging.getLogger(__name__)

JWT_ALGORITHM = "HS256"


class PasswordHasher:
    """Encapsulates bcrypt hashing so call sites never touch bcrypt directly."""

    def hash(self, password: str) -> str:
        hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
        return hashed.decode("utf-8")

    def verify(self, password: str, hashed: str) -> bool:
        try:
            return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
        except (ValueError, TypeError):
            logger.warning("Password verification received a malformed hash")
            return False


class TokenService:
    """Encapsulates JWT issuing/validation for a given secret and TTL."""

    def __init__(self, secret: str, exp_minutes: int):
        self._secret = secret
        self._exp_minutes = exp_minutes

    def generate(self, user_id: int, role: str) -> str:
        now = datetime.now(timezone.utc)
        claims = {
            "user_id": user_id,
            "role": role,
            "exp": now + timedelta(minutes=self._exp_minutes),
            "iat": now,
        }
        return jwt.encode(claims, self._secret, algorithm=JWT_ALGORITHM)

    def decode(self, token: str) -> dict | None:
        try:
            return jwt.decode(token, self._secret, algorithms=[JWT_ALGORITHM])
        except jwt.PyJWTError as exc:
            logger.info("Token validation failed: %s", exc.__class__.__name__)
            return None


_password_hasher = PasswordHasher()
_token_service = TokenService(config.JWT_SECRET, config.JWT_EXP_MINUTES)


def hash_password(password: str) -> str:
    return _password_hasher.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return _password_hasher.verify(password, hashed)


def generate_token(user_id: int, role: str) -> str:
    return _token_service.generate(user_id, role)


def decode_token(token: str) -> dict | None:
    return _token_service.decode(token)


def _extract_bearer_token() -> str | None:
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        return None
    return header[len("Bearer "):].strip() or None


def login_required(view_func):
    """Require a valid `Authorization: Bearer <jwt>` header.

    On success, sets `flask.g.user_id` and `flask.g.role`. On failure,
    raises AuthenticationError, which the global error handler converts
    to a 401 JSON envelope.
    """

    @wraps(view_func)
    def wrapper(*args, **kwargs):
        token = _extract_bearer_token()
        if not token:
            raise AuthenticationError("Missing bearer token")
        claims = decode_token(token)
        if not claims:
            raise AuthenticationError("Invalid or expired token")
        g.user_id = claims.get("user_id")
        g.role = claims.get("role")
        return view_func(*args, **kwargs)

    return wrapper


def role_required(role: str):
    """Require `flask.g.role == role`. Must be applied after `login_required`."""

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(*args, **kwargs):
            if getattr(g, "role", None) != role:
                raise UnauthorizedError(f"Requires role '{role}'")
            return view_func(*args, **kwargs)

        return wrapper

    return decorator
