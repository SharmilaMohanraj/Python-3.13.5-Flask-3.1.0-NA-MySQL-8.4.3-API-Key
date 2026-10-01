"""Student enrollment endpoint.

Thin HTTP layer only: verifies the course exists, delegates the
one-enrollment-per-student-per-course rule to the model layer, and
translates its ValueError into the shared 409 DuplicateEnrollmentError.
"""
import logging

from flask import Blueprint, g, jsonify

from auth import login_required, role_required
from errors import DuplicateEnrollmentError, NotFoundError
from models import course_model, enrollment_model

logger = logging.getLogger(__name__)

enrollment_bp = Blueprint("enrollment_bp", __name__)


def _serialize(enrollment: dict) -> dict:
    enrolled_at = enrollment.get("enrolled_at")
    return {
        "id": enrollment["id"],
        "student_id": enrollment["student_id"],
        "course_id": enrollment["course_id"],
        "enrolled_at": enrolled_at.isoformat() if hasattr(enrolled_at, "isoformat") else enrolled_at,
        "status": enrollment["status"],
    }


@enrollment_bp.route("/courses/<int:course_id>/enroll", methods=["POST"])
@login_required
@role_required("student")
def enroll(course_id: int):
    """Enroll the authenticated student in `course_id`."""
    course = course_model.get_course(course_id)
    if course is None:
        raise NotFoundError(f"Course {course_id} not found")

    try:
        enrollment_model.create_enrollment(g.user_id, course_id)
    except ValueError as exc:
        raise DuplicateEnrollmentError("Already enrolled in this course") from exc

    enrollment = enrollment_model.get_enrollment(g.user_id, course_id)
    logger.info("Student user_id=%s enrolled in course_id=%s", g.user_id, course_id)
    return jsonify(_serialize(enrollment)), 201
