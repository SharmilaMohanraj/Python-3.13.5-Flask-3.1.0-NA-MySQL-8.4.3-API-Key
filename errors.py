"""Domain exception hierarchy.

Routes and models raise these instead of generic Exception/ValueError so
the centralized error handler in app.py can translate them into a single,
consistent HTTP response envelope without ever inspecting a raw message
string. See app.py's `register_error_handlers`.
"""


class AppError(Exception):
    """Base class for all domain-level, intentionally-raised errors.

    Carries everything the global error handler needs to build the
    standard envelope: an HTTP status code, a machine-readable error code,
    and a client-safe message.
    """

    status_code: int = 500
    code: str = "INTERNAL_ERROR"

    def __init__(self, message: str, *, code: str | None = None, status_code: int | None = None):
        super().__init__(message)
        self.message = message
        if code is not None:
            self.code = code
        if status_code is not None:
            self.status_code = status_code


class ValidationError(AppError):
    status_code = 400
    code = "VALIDATION_ERROR"


class AuthenticationError(AppError):
    status_code = 401
    code = "AUTHENTICATION_ERROR"


class UnauthorizedError(AppError):
    """Caller is authenticated but not allowed to perform this action."""

    status_code = 403
    code = "UNAUTHORIZED"


class NotFoundError(AppError):
    status_code = 404
    code = "NOT_FOUND"


class ConflictError(AppError):
    status_code = 409
    code = "CONFLICT"


class DuplicateEnrollmentError(ConflictError):
    code = "DUPLICATE_ENROLLMENT"
