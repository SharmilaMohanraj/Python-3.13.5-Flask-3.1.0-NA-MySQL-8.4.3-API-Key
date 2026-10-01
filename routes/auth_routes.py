"""Public authentication endpoints: registration and login.

Thin HTTP layer only — validation and response shaping happen here;
all persistence goes through `models.user_model`, and all
hashing/token concerns go through `auth`. No SQL lives in this file.
"""
import logging

from flask import Blueprint, jsonify, request

import auth
from errors import AuthenticationError, ConflictError, ValidationError
from models import user_model

logger = logging.getLogger(__name__)

auth_bp = Blueprint("auth_bp", __name__)

ROLE_INSTRUCTOR = "instructor"
ROLE_STUDENT = "student"
VALID_ROLES = (ROLE_INSTRUCTOR, ROLE_STUDENT)


class RegistrationValidator:
    """Validates the JSON body for POST /auth/register."""

    def validate(self, payload: dict) -> tuple[str, str, str, str]:
        name = payload.get("name")
        email = payload.get("email")
        password = payload.get("password")
        role = payload.get("role")

        for field_name, value in (
            ("name", name),
            ("email", email),
            ("password", password),
            ("role", role),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValidationError(f"Field '{field_name}' is required and must be a non-empty string")

        if role not in VALID_ROLES:
            raise ValidationError(f"Field 'role' must be one of {VALID_ROLES}")

        return name, email, password, role


class LoginValidator:
    """Validates the JSON body for POST /auth/login."""

    def validate(self, payload: dict) -> tuple[str, str]:
        email = payload.get("email")
        password = payload.get("password")

        for field_name, value in (("email", email), ("password", password)):
            if not isinstance(value, str) or not value.strip():
                raise ValidationError(f"Field '{field_name}' is required and must be a non-empty string")

        return email, password


_registration_validator = RegistrationValidator()
_login_validator = LoginValidator()


@auth_bp.route("/auth/register", methods=["POST"])
def register():
    """Register a new user (instructor or student) and return a JWT."""
    payload = request.get_json(silent=True) or {}
    name, email, password, role = _registration_validator.validate(payload)

    password_hash = auth.hash_password(password)

    try:
        user_id = user_model.create_user(name, email, password_hash, role)
    except ValueError as exc:
        raise ConflictError("Email already registered") from exc

    token = auth.generate_token(user_id, role)
    logger.info("User registered: id=%s role=%s", user_id, role)

    return (
        jsonify({"id": user_id, "name": name, "email": email, "role": role, "token": token}),
        201,
    )


@auth_bp.route("/auth/login", methods=["POST"])
def login():
    """Authenticate a user by email/password and return a JWT."""
    payload = request.get_json(silent=True) or {}
    email, password = _login_validator.validate(payload)

    user = user_model.get_user_by_email(email)
    if user is None or not auth.verify_password(password, user["password_hash"]):
        raise AuthenticationError("Invalid email or password")

    token = auth.generate_token(user["id"], user["role"])
    logger.info("User logged in: id=%s role=%s", user["id"], user["role"])

    return (
        jsonify(
            {
                "token": token,
                "user": {
                    "id": user["id"],
                    "name": user["name"],
                    "email": user["email"],
                    "role": user["role"],
                },
            }
        ),
        200,
    )
