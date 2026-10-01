"""Flask Blueprint exposing module creation scoped to a course.

Route layer stays thin: validation + authorization only, all persistence
and ownership lookups delegate to the model layer.
"""
import logging

from flask import Blueprint, g, jsonify, request

from auth import login_required, role_required
from errors import NotFoundError, UnauthorizedError, ValidationError
from models import course_model, lesson_model, module_model

logger = logging.getLogger(__name__)

module_bp = Blueprint("modules", __name__)


class ModuleCreateRequest:
    """Validates and holds the payload for creating a module."""

    def __init__(self, payload: dict):
        title = (payload or {}).get("title")
        order_index = (payload or {}).get("order_index")

        if not title or not isinstance(title, str):
            raise ValidationError("'title' is required and must be a non-empty string")
        if order_index is None or not isinstance(order_index, int):
            raise ValidationError("'order_index' is required and must be an integer")

        self.title = title
        self.order_index = order_index


class CourseOwnershipGuard:
    """Verifies that an authenticated instructor owns a course."""

    def ensure_owner(self, course_id: int, instructor_id: int) -> dict:
        course = course_model.get_course(course_id)
        if not course:
            raise NotFoundError(f"Course {course_id} not found")

        if course["instructor_id"] != instructor_id:
            raise UnauthorizedError("You do not own this course")

        return course


_ownership_guard = CourseOwnershipGuard()


@module_bp.route("/courses/<int:course_id>/modules", methods=["POST"])
@login_required
@role_required("instructor")
def create_module(course_id: int):
    _ownership_guard.ensure_owner(course_id, g.user_id)

    module_request = ModuleCreateRequest(request.get_json(silent=True))
    module_id = module_model.create_module(course_id, module_request.title, module_request.order_index)
    module = module_model.get_module(module_id)

    logger.info("Instructor user_id=%s created module_id=%s in course_id=%s", g.user_id, module_id, course_id)
    return jsonify(module), 201


@module_bp.route("/courses/<int:course_id>/modules", methods=["GET"])
@login_required
def list_modules(course_id: int):
    """List modules for a course, ordered by order_index, each with its
    lessons nested (ordered by lesson order_index).
    """
    course = course_model.get_course(course_id)
    if not course:
        raise NotFoundError(f"Course {course_id} not found")

    modules = module_model.list_modules_for_course(course_id)
    for module in modules:
        module["lessons"] = lesson_model.list_lessons_for_module(module["id"])
    return jsonify(modules), 200
