"""Enrollment data-access layer.

Wraps raw SQL access to the `enrollments` table behind a small repository
class, with module-level function wrappers exposing the stable call
surface used by `routes/enrollment_routes.py`, `routes/course_routes.py`
(stats endpoint) and `models/progress_model.py` (completion cascade):
`create_enrollment`, `get_enrollment`, `set_enrollment_status`,
`count_enrollments`, `count_completed_enrollments`, `completion_rate`.

One active enrollment per (student, course) is enforced by the
`uq_enrollments_student_course` unique constraint; a duplicate insert is
translated here into a plain `ValueError`, which the route layer turns
into a 409 `DuplicateEnrollmentError`.
"""
import logging

import pymysql

from db import execute, query_one

logger = logging.getLogger(__name__)

_DUPLICATE_ENTRY_ERRNO = 1062


class EnrollmentRepository:
    """Encapsulates all SQL statements touching the `enrollments` table."""

    def create(self, student_id: int, course_id: int) -> int:
        """Insert a new 'active' enrollment, returning its id.

        Raises:
            ValueError: if the student is already enrolled in the course.
        """
        try:
            enrollment_id = execute(
                "INSERT INTO enrollments (student_id, course_id, status, enrolled_at) "
                "VALUES (%s, %s, 'active', NOW())",
                (student_id, course_id),
            )
        except pymysql.err.IntegrityError as exc:
            if exc.args and exc.args[0] == _DUPLICATE_ENTRY_ERRNO:
                logger.info("Duplicate enrollment attempt student_id=%s course_id=%s", student_id, course_id)
                raise ValueError(f"Student {student_id} is already enrolled in course {course_id}") from exc
            raise

        logger.info("Created enrollment id=%s student_id=%s course_id=%s", enrollment_id, student_id, course_id)
        return enrollment_id

    def find(self, student_id: int, course_id: int) -> dict | None:
        return query_one(
            "SELECT * FROM enrollments WHERE student_id = %s AND course_id = %s",
            (student_id, course_id),
        )

    def set_status(self, student_id: int, course_id: int, status: str) -> None:
        execute(
            "UPDATE enrollments SET status = %s WHERE student_id = %s AND course_id = %s",
            (status, student_id, course_id),
        )
        logger.info("Enrollment status updated student_id=%s course_id=%s status=%s", student_id, course_id, status)

    def count(self, course_id: int) -> int:
        row = query_one("SELECT COUNT(*) AS cnt FROM enrollments WHERE course_id = %s", (course_id,))
        return row["cnt"] if row else 0

    def count_completed(self, course_id: int) -> int:
        row = query_one(
            "SELECT COUNT(*) AS cnt FROM enrollments WHERE course_id = %s AND status = 'completed'",
            (course_id,),
        )
        return row["cnt"] if row else 0


_repository = EnrollmentRepository()


def create_enrollment(student_id: int, course_id: int) -> int:
    """Enroll `student_id` in `course_id` with status='active'.

    Returns the new enrollment id. Raises ValueError if already enrolled.
    """
    return _repository.create(student_id, course_id)


def get_enrollment(student_id: int, course_id: int) -> dict | None:
    """Return the enrollment row for (student_id, course_id), or None."""
    return _repository.find(student_id, course_id)


def set_enrollment_status(student_id: int, course_id: int, status: str) -> None:
    """Update an enrollment's status to 'active' or 'completed'."""
    _repository.set_status(student_id, course_id, status)


def count_enrollments(course_id: int) -> int:
    """Return the total number of enrollments for `course_id`."""
    return _repository.count(course_id)


def count_completed_enrollments(course_id: int) -> int:
    """Return the number of enrollments with status='completed' for `course_id`."""
    return _repository.count_completed(course_id)


def completion_rate(course_id: int) -> float:
    """Return the percentage (0.0-100.0) of enrollments that are completed.

    Returns 0.0 if there are no enrollments.
    """
    total = count_enrollments(course_id)
    if total == 0:
        return 0.0
    completed = count_completed_enrollments(course_id)
    return (completed / total) * 100.0
