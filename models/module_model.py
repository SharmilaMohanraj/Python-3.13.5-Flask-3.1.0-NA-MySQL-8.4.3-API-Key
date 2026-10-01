"""Data access for modules within a course.

Thin repository-style wrapper around db.py's raw-SQL helpers. Modules are
instructor-authored structure units ordered within a course via
`order_index`.
"""
import logging

from db import execute, query_all, query_one

logger = logging.getLogger(__name__)


class ModuleRepository:
    """Encapsulates all SQL for the `modules` table."""

    def create(self, course_id: int, title: str, order_index: int) -> int:
        module_id = execute(
            "INSERT INTO modules (course_id, title, order_index) VALUES (%s, %s, %s)",
            (course_id, title, order_index),
        )
        logger.info("Created module id=%s in course_id=%s", module_id, course_id)
        return module_id

    def get(self, module_id: int) -> dict | None:
        return query_one(
            "SELECT id, course_id, title, order_index FROM modules WHERE id = %s",
            (module_id,),
        )

    def list_for_course(self, course_id: int) -> list[dict]:
        return query_all(
            "SELECT id, course_id, title, order_index FROM modules "
            "WHERE course_id = %s ORDER BY order_index ASC",
            (course_id,),
        )

    def count_for_course(self, course_id: int) -> int:
        row = query_one(
            "SELECT COUNT(*) AS module_count FROM modules WHERE course_id = %s",
            (course_id,),
        )
        return row["module_count"] if row else 0

    def list_ids_for_course(self, course_id: int) -> list[int]:
        rows = query_all(
            "SELECT id FROM modules WHERE course_id = %s ORDER BY order_index ASC",
            (course_id,),
        )
        return [row["id"] for row in rows]


_repository = ModuleRepository()


def create_module(course_id: int, title: str, order_index: int) -> int:
    """Create a module under `course_id`, returning the new module id."""
    return _repository.create(course_id, title, order_index)


def get_module(module_id: int) -> dict | None:
    """Return the module dict (id, course_id, title, order_index) or None."""
    return _repository.get(module_id)


def list_modules_for_course(course_id: int) -> list[dict]:
    """Return modules for `course_id`, ordered by order_index ascending."""
    return _repository.list_for_course(course_id)


def count_modules_in_course(course_id: int) -> int:
    """Return the number of modules belonging to `course_id`."""
    return _repository.count_for_course(course_id)


def list_module_ids_for_course(course_id: int) -> list[int]:
    """Return the ids of every module belonging to `course_id`, ordered by order_index."""
    return _repository.list_ids_for_course(course_id)
