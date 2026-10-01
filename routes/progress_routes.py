"""Lesson progress endpoint, including the auto-completion cascade response."""
import logging

from flask import Blueprint, g, jsonify, request

from auth import login_required, role_required
from errors import NotFoundError, ValidationError
from models import lesson_model, progress_model

logger = logging.getLogger(__name__)

progress_bp = Blueprint("progress_bp", __name__)


@progress_bp.route("/lessons/<int:lesson_id>/progress", methods=["PUT"])
@login_required
@role_required("student")
def update_progress(lesson_id: int):
    """Update the authenticated student's progress on a lesson.

    Triggers the module/course/certificate auto-completion cascade when
    the new status is 'COMPLETED'.
    """
    lesson = lesson_model.get_lesson(lesson_id)
    if lesson is None:
        raise NotFoundError(f"Lesson {lesson_id} not found")

    body = request.get_json(silent=True) or {}
    status = body.get("status")
    if not isinstance(status, str) or not status:
        raise ValidationError("Field 'status' is required")

    try:
        progress = progress_model.upsert_lesson_progress(g.user_id, lesson_id, status)
    except ValueError as exc:
        raise ValidationError(str(exc)) from exc

    logger.info("Progress updated: student_id=%s lesson_id=%s status=%s", g.user_id, lesson_id, status)
    return jsonify(progress), 200
