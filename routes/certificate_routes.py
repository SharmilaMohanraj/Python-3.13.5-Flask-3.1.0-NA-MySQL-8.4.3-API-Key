"""Certificate retrieval endpoint."""
import logging

from flask import Blueprint, g, jsonify

from auth import login_required
from errors import UnauthorizedError
from models import certificate_model

logger = logging.getLogger(__name__)

certificate_bp = Blueprint("certificate_bp", __name__)


@certificate_bp.route("/students/<int:student_id>/certificates", methods=["GET"])
@login_required
def list_certificates(student_id: int):
    """Return every certificate earned by `student_id`.

    A student may only view their own certificates; an instructor may
    view any student's certificates.
    """
    if g.role == "student" and g.user_id != student_id:
        raise UnauthorizedError("Students may only view their own certificates")
    if g.role not in ("student", "instructor"):
        raise UnauthorizedError("Not permitted")

    certificates = certificate_model.list_certificates_for_student(student_id)
    serialized = [
        {
            "id": c["id"],
            "student_id": c["student_id"],
            "course_id": c["course_id"],
            "issued_at": c["issued_at"].isoformat() if hasattr(c["issued_at"], "isoformat") else c["issued_at"],
        }
        for c in certificates
    ]
    return jsonify(serialized), 200
