"""Course Blueprint: creation, search, detail, and per-course stats.

Thin HTTP layer: validates input, enforces auth/ownership, and delegates
to the model layer for all data access and aggregation.
"""
import logging

from flask import Blueprint, g, jsonify, request

from auth import login_required, role_required
from errors import NotFoundError, UnauthorizedError, ValidationError
from models import course_model, enrollment_model, lesson_model, module_model

logger = logging.getLogger(__name__)

course_bp = Blueprint("courses", __name__)

_VALID_ENROLLMENT_STATUSES = {"enrolled", "not_enrolled"}


def _get_json_body() -> dict:
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        raise ValidationError("Request body must be a JSON object")
    return body


def _require_owned_course(course_id: int) -> dict:
    """Return the course dict for `course_id`, raising NotFoundError or
    UnauthorizedError if it doesn't exist or isn't owned by the caller.
    """
    course = course_model.get_course(course_id)
    if course is None:
        raise NotFoundError(f"Course {course_id} not found")
    if course["instructor_id"] != g.user_id:
        raise UnauthorizedError("You do not own this course")
    return course


@course_bp.route("/courses", methods=["POST"])
@login_required
@role_required("instructor")
def create_course():
    """Instructor creates a new course."""
    body = _get_json_body()
    title = (body.get("title") or "").strip()
    if not title:
        raise ValidationError("Field 'title' is required")
    description = body.get("description")
    category = body.get("category")

    course_id = course_model.create_course(
        instructor_id=g.user_id,
        title=title,
        description=description,
        category=category,
    )
    course = course_model.get_course(course_id)
    logger.info("Instructor user_id=%s created course id=%s", g.user_id, course_id)
    return jsonify(course), 201


@course_bp.route("/courses", methods=["GET"])
@login_required
def search_courses():
    """List/search courses, optionally filtered by category and the
    caller's own enrollment status.
    """
    category = request.args.get("category") or None
    enrollment_status = request.args.get("enrollment_status") or None

    if enrollment_status is not None and enrollment_status not in _VALID_ENROLLMENT_STATUSES:
        raise ValidationError("Query param 'enrollment_status' must be 'enrolled' or 'not_enrolled'")

    # Students always get their enrollment status annotated on each course,
    # regardless of whether they're also filtering by it.
    student_id = g.user_id if g.role == "student" else None
    courses = course_model.search_courses(
        category=category,
        student_id=student_id,
        enrollment_status=enrollment_status,
    )
    return jsonify(courses), 200


@course_bp.route("/courses/<int:course_id>", methods=["GET"])
@login_required
def get_course_detail(course_id: int):
    """Return a course plus its modules, each with nested lessons, ordered
    by order_index.
    """
    course = course_model.get_course(course_id)
    if course is None:
        raise NotFoundError(f"Course {course_id} not found")

    modules = module_model.list_modules_for_course(course_id)
    for module in modules:
        module["lessons"] = lesson_model.list_lessons_for_module(module["id"])

    response = dict(course)
    response["modules"] = modules
    return jsonify(response), 200


@course_bp.route("/courses/<int:course_id>/stats", methods=["GET"])
@login_required
@role_required("instructor")
def get_course_stats(course_id: int):
    """Instructor views enrollment count and completion rate for a course
    they own.
    """
    _require_owned_course(course_id)

    enrollment_count = enrollment_model.count_enrollments(course_id)
    completed_count = enrollment_model.count_completed_enrollments(course_id)
    # This endpoint reports a 0.0-1.0 fraction (distinct from
    # enrollment_model.completion_rate's own 0-100 percentage, which other
    # callers may use).
    rate = (completed_count / enrollment_count) if enrollment_count else 0.0

    return jsonify({
        "enrollment_count": enrollment_count,
        "completed_count": completed_count,
        "completion_rate": rate,
    }), 200
