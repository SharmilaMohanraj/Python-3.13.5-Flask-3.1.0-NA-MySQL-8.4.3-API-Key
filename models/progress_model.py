"""Progress tracking data access plus the cascade-completion business logic.

This module is the designated business/service layer for the completion
cascade and is the one place in the app allowed to orchestrate across
`lesson_model`, `module_model`, `enrollment_model` and `certificate_model`:

    lesson marked COMPLETED
        -> is every lesson in its module now COMPLETED for this student?
           -> stamp `module_completed=True` onto every lesson_progress row
              this student has in that module
        -> is every module in the course now complete for this student?
           -> flip the enrollment to 'completed'
           -> idempotently issue the student's certificate for the course

All of that happens inside `upsert_lesson_progress`; routes stay thin and
only call into this function.
"""
import logging

from db import execute, query_all, query_one
from models import certificate_model, enrollment_model, lesson_model, module_model

logger = logging.getLogger(__name__)

VALID_STATUSES = ("NOT_STARTED", "IN_PROGRESS", "COMPLETED")

_COLUMNS = "id, student_id, lesson_id, status, module_completed, updated_at"


class ProgressRepository:
    """Encapsulates all SQL for the `lesson_progress` table."""

    def find(self, student_id: int, lesson_id: int) -> dict | None:
        return query_one(
            f"SELECT {_COLUMNS} FROM lesson_progress WHERE student_id = %s AND lesson_id = %s",
            (student_id, lesson_id),
        )

    def upsert_status(self, student_id: int, lesson_id: int, status: str) -> None:
        execute(
            "INSERT INTO lesson_progress (student_id, lesson_id, status, module_completed, updated_at) "
            "VALUES (%s, %s, %s, FALSE, NOW()) "
            "ON DUPLICATE KEY UPDATE status = VALUES(status), updated_at = NOW()",
            (student_id, lesson_id, status),
        )

    def module_already_completed(self, student_id: int, module_id: int) -> bool:
        row = query_one(
            "SELECT lp.module_completed AS module_completed FROM lesson_progress lp "
            "JOIN lessons l ON l.id = lp.lesson_id "
            "WHERE l.module_id = %s AND lp.student_id = %s AND lp.module_completed = TRUE "
            "LIMIT 1",
            (module_id, student_id),
        )
        return row is not None

    def count_completed_lessons_in_module(self, student_id: int, module_id: int) -> int:
        row = query_one(
            "SELECT COUNT(*) AS cnt FROM lesson_progress lp "
            "JOIN lessons l ON l.id = lp.lesson_id "
            "WHERE l.module_id = %s AND lp.student_id = %s AND lp.status = 'COMPLETED'",
            (module_id, student_id),
        )
        return row["cnt"] if row else 0

    def count_module_completed_flags(self, student_id: int, module_id: int) -> int:
        row = query_one(
            "SELECT COUNT(*) AS cnt FROM lesson_progress lp "
            "JOIN lessons l ON l.id = lp.lesson_id "
            "WHERE l.module_id = %s AND lp.student_id = %s AND lp.module_completed = TRUE",
            (module_id, student_id),
        )
        return row["cnt"] if row else 0

    def mark_module_completed(self, student_id: int, module_id: int) -> None:
        execute(
            "UPDATE lesson_progress lp JOIN lessons l ON l.id = lp.lesson_id "
            "SET lp.module_completed = TRUE "
            "WHERE l.module_id = %s AND lp.student_id = %s",
            (module_id, student_id),
        )

    def list_for_course(self, student_id: int, course_id: int) -> list[dict]:
        return query_all(
            "SELECT lp.id, lp.student_id, lp.lesson_id, lp.status, lp.module_completed, lp.updated_at "
            "FROM lesson_progress lp "
            "JOIN lessons l ON l.id = lp.lesson_id "
            "JOIN modules m ON m.id = l.module_id "
            "WHERE lp.student_id = %s AND m.course_id = %s "
            "ORDER BY m.order_index ASC, l.order_index ASC",
            (student_id, course_id),
        )


_repository = ProgressRepository()


def _serialize(row: dict, module_completed_now: bool, course_completed_now: bool) -> dict:
    updated_at = row.get("updated_at")
    return {
        "id": row["id"],
        "student_id": row["student_id"],
        "lesson_id": row["lesson_id"],
        "status": row["status"],
        "module_completed": bool(row["module_completed"]),
        "updated_at": updated_at.isoformat() if hasattr(updated_at, "isoformat") else updated_at,
        "module_completed_now": module_completed_now,
        "course_completed_now": course_completed_now,
    }


def _is_module_complete_for_student(student_id: int, module_id: int) -> bool:
    """A module counts as complete for a student iff it has at least one
    lesson and every one of its lessons has `module_completed=True`.
    """
    total_lessons = lesson_model.count_lessons_in_module(module_id)
    if total_lessons == 0:
        return False
    flagged = _repository.count_module_completed_flags(student_id, module_id)
    return flagged == total_lessons


def upsert_lesson_progress(student_id: int, lesson_id: int, status: str) -> dict:
    """Insert or update a student's progress on one lesson, running the
    module -> course -> certificate completion cascade when `status` is
    'COMPLETED'.

    Raises:
        ValueError: if `status` isn't one of the three valid values.
    """
    if status not in VALID_STATUSES:
        raise ValueError(f"Invalid status '{status}', must be one of {VALID_STATUSES}")

    _repository.upsert_status(student_id, lesson_id, status)

    module_completed_now = False
    course_completed_now = False

    if status == "COMPLETED":
        lesson = lesson_model.get_lesson(lesson_id)
        module_id = lesson["module_id"]

        total_lessons = lesson_model.count_lessons_in_module(module_id)
        completed_lessons = _repository.count_completed_lessons_in_module(student_id, module_id)

        if total_lessons > 0 and completed_lessons == total_lessons:
            was_already_complete = _repository.module_already_completed(student_id, module_id)
            _repository.mark_module_completed(student_id, module_id)
            if not was_already_complete:
                module_completed_now = True
                logger.info("Module auto-completed: student_id=%s module_id=%s", student_id, module_id)

            module = module_model.get_module(module_id)
            course_id = module["course_id"]
            module_ids = module_model.list_module_ids_for_course(course_id)

            course_complete = len(module_ids) > 0 and all(
                _is_module_complete_for_student(student_id, mid) for mid in module_ids
            )

            if course_complete:
                had_certificate = certificate_model.get_certificate(student_id, course_id) is not None
                enrollment_model.set_enrollment_status(student_id, course_id, "completed")
                certificate_model.create_certificate(student_id, course_id)
                if not had_certificate:
                    course_completed_now = True
                    logger.info("Course auto-completed: student_id=%s course_id=%s", student_id, course_id)

    row = _repository.find(student_id, lesson_id)
    return _serialize(row, module_completed_now, course_completed_now)


def get_progress(student_id: int, lesson_id: int) -> dict | None:
    """Return a student's progress row for one lesson, or None if untouched."""
    row = _repository.find(student_id, lesson_id)
    if row is None:
        return None
    return _serialize(row, module_completed_now=False, course_completed_now=False)


def list_progress_for_student_course(student_id: int, course_id: int) -> list[dict]:
    """Return every progress record a student has within a course."""
    rows = _repository.list_for_course(student_id, course_id)
    return [_serialize(row, module_completed_now=False, course_completed_now=False) for row in rows]
