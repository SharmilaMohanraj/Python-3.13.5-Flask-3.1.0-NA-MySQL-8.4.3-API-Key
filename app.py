"""Flask application factory and entry point for the LMS REST API."""
import logging
import uuid
from datetime import datetime, timezone

from flask import Flask, g, jsonify, request
from werkzeug.exceptions import HTTPException

from config import config
from errors import AppError
from routes.auth_routes import auth_bp
from routes.certificate_routes import certificate_bp
from routes.course_routes import course_bp
from routes.docs_routes import docs_bp
from routes.enrollment_routes import enrollment_bp
from routes.lesson_routes import lesson_bp
from routes.module_routes import module_bp
from routes.progress_routes import progress_bp

logger = logging.getLogger(__name__)


def _configure_logging() -> None:
    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s [correlation_id=%(correlation_id)s] %(message)s",
    )
    # A Filter attached to a *logger* only runs for records logged directly
    # on that logger, not ones propagated from children — attach it to the
    # root logger's handler(s) instead so every module's logger is covered.
    correlation_filter = _CorrelationIdFilter()
    for handler in logging.getLogger().handlers:
        handler.addFilter(correlation_filter)


class _CorrelationIdFilter(logging.Filter):
    """Injects the current request's correlation id into every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            record.correlation_id = getattr(g, "correlation_id", "-")
        except RuntimeError:
            record.correlation_id = "-"
        return True


def _error_envelope(message: str, code: str, status_code: int) -> tuple:
    correlation_id = getattr(g, "correlation_id", "-")
    body = {
        "error": message,
        "code": code,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "correlation_id": correlation_id,
    }
    return jsonify(body), status_code


def register_error_handlers(app: Flask) -> None:
    """One centralized place turning every exception into the standard
    {error, code, timestamp, correlation_id} JSON envelope.
    """

    @app.errorhandler(AppError)
    def handle_app_error(exc: AppError):
        logger.warning("Handled AppError: %s (%s)", exc.message, exc.code)
        return _error_envelope(exc.message, exc.code, exc.status_code)

    @app.errorhandler(HTTPException)
    def handle_http_exception(exc: HTTPException):
        logger.warning("Handled HTTPException: %s", exc.description)
        return _error_envelope(exc.description or exc.name, exc.name.upper().replace(" ", "_"), exc.code or 500)

    @app.errorhandler(Exception)
    def handle_unexpected_exception(exc: Exception):
        logger.exception("Unhandled exception")
        return _error_envelope("Internal server error", "INTERNAL_ERROR", 500)


def create_app() -> Flask:
    """Application factory: builds the Flask app, wires blueprints, logging
    and the centralized error handler.
    """
    _configure_logging()

    app = Flask(__name__)

    @app.before_request
    def _assign_correlation_id():
        g.correlation_id = (
            request.headers.get("X-Request-ID")
            or request.headers.get("X-Correlation-ID")
            or str(uuid.uuid4())
        )

    @app.after_request
    def _echo_correlation_id(response):
        response.headers["X-Correlation-ID"] = getattr(g, "correlation_id", "-")
        return response

    register_error_handlers(app)

    app.register_blueprint(docs_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(course_bp)
    app.register_blueprint(module_bp)
    app.register_blueprint(lesson_bp)
    app.register_blueprint(enrollment_bp)
    app.register_blueprint(progress_bp)
    app.register_blueprint(certificate_bp)

    logger.info("LMS API application created")
    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
