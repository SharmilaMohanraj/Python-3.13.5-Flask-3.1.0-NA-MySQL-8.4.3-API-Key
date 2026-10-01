"""Data access for courses.

Thin repository-style wrapper around db.py's raw-SQL helpers. Courses are
created by instructors and searched/browsed by students, optionally
filtered by category and by the caller's own enrollment status.
"""
import logging

from db import execute, query_all, query_one

logger = logging.getLogger(__name__)


class CourseRepository:
    """Encapsulates all SQL for the `courses` table."""

    _COLUMNS = "id, instructor_id, title, description, category"

    def create(self, instructor_id: int, title: str, description: str, category: str) -> int:
        course_id = execute(
            "INSERT INTO courses (instructor_id, title, description, category) "
            "VALUES (%s, %s, %s, %s)",
            (instructor_id, title, description, category),
        )
        logger.info("Created course id=%s for instructor_id=%s", course_id, instructor_id)
        return course_id

    def get(self, course_id: int) -> dict | None:
        return query_one(
            f"SELECT {self._COLUMNS} FROM courses WHERE id = %s",
            (course_id,),
        )

    def search(
        self,
        category: str | None = None,
        student_id: int | None = None,
        enrollment_status: str | None = None,
    ) -> list[dict]:
        join_clause = ""
        select_extra = ""
        conditions = []
        params: list = []

        if student_id is not None:
            # Always LEFT JOIN so every course can be annotated with the
            # caller's enrollment status, regardless of whether they're
            # also filtering by it.
            join_clause = "LEFT JOIN enrollments e ON e.course_id = courses.id AND e.student_id = %s"
            params.append(student_id)
            select_extra = ", (e.id IS NOT NULL) AS enrolled"

            if enrollment_status == "enrolled":
                conditions.append("e.id IS NOT NULL")
            elif enrollment_status == "not_enrolled":
                conditions.append("e.id IS NULL")

        if category:
            conditions.append("courses.category = %s")
            params.append(category)

        sql = (
            "SELECT courses.id, courses.instructor_id, courses.title, "
            f"courses.description, courses.category{select_extra} FROM courses"
        )
        if join_clause:
            sql += f" {join_clause}"
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        sql += " ORDER BY courses.id ASC"

        rows = query_all(sql, tuple(params))
        if student_id is not None:
            for row in rows:
                row["enrolled"] = bool(row["enrolled"])
        return rows


_repository = CourseRepository()


def create_course(instructor_id: int, title: str, description: str, category: str) -> int:
    """Create a course owned by `instructor_id`, returning the new course id."""
    return _repository.create(instructor_id, title, description, category)


def get_course(course_id: int) -> dict | None:
    """Return the course dict (id, instructor_id, title, description, category) or None."""
    return _repository.get(course_id)


def search_courses(
    category: str | None = None,
    student_id: int | None = None,
    enrollment_status: str | None = None,
) -> list[dict]:
    """Return courses filtered by `category` and, when `student_id` and
    `enrollment_status` ('enrolled'|'not_enrolled') are both given, by
    whether an enrollment row exists for that student.
    """
    return _repository.search(category=category, student_id=student_id, enrollment_status=enrollment_status)
