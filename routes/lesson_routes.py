"""Flask Blueprint exposing lesson creation scoped to a module.

Route layer stays thin: validation + authorization only, all persistence
and ownership lookups delegate to the model layer.
"""
import logging

from flask import Blueprint, g, jsonify, request

from auth import login_required, role_required
from errors import NotFoundError, UnauthorizedError, ValidationError
from models import course_model, lesson_model, module_model

logger = logging.getLogger(__name__)

lesson_bp = Blueprint("lessons", __name__)


class LessonCreateRequest:
    """Validates and holds the payload for creating a lesson."""

    def __init__(self, payload: dict):
        title = (payload or {}).get("title")
        order_index = (payload or {}).get("order_index")

        if not title or not isinstance(title, str):
            raise ValidationError("'title' is required and must be a non-empty string")
        if order_index is None or not isinstance(order_index, int):
            raise ValidationError("'order_index' is required and must be an integer")

        self.title = title
        self.order_index = order_index


class ModuleOwnershipGuard:
    """Verifies that an authenticated instructor owns a module's course."""

    def ensure_owner(self, module_id: int, instructor_id: int) -> dict:
        module = module_model.get_module(module_id)
        if not module:
            raise NotFoundError(f"Module {module_id} not found")

        course = course_model.get_course(module["course_id"])
        if not course:
            raise NotFoundError(f"Course {module['course_id']} not found")

        if course["instructor_id"] != instructor_id:
            raise UnauthorizedError("You do not own the course for this module")

        return module


_ownership_guard = ModuleOwnershipGuard()


@lesson_bp.route("/modules/<int:module_id>/lessons", methods=["POST"])
@login_required
@role_required("instructor")
def create_lesson(module_id: int):
    _ownership_guard.ensure_owner(module_id, g.user_id)

    lesson_request = LessonCreateRequest(request.get_json(silent=True))
    lesson_id = lesson_model.create_lesson(module_id, lesson_request.title, lesson_request.order_index)
    lesson = lesson_model.get_lesson(lesson_id)

    logger.info("Instructor user_id=%s created lesson_id=%s in module_id=%s", g.user_id, lesson_id, module_id)
    return jsonify(lesson), 201
