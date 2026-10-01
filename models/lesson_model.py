"""Data access for lessons within a module.

Thin repository-style wrapper around db.py's raw-SQL helpers. Lessons are
instructor-authored content ordered within a module via `order_index`.
"""
import logging

from db import execute, query_all, query_one

logger = logging.getLogger(__name__)


class LessonRepository:
    """Encapsulates all SQL for the `lessons` table."""

    def create(self, module_id: int, title: str, order_index: int) -> int:
        lesson_id = execute(
            "INSERT INTO lessons (module_id, title, order_index) VALUES (%s, %s, %s)",
            (module_id, title, order_index),
        )
        logger.info("Created lesson id=%s in module_id=%s", lesson_id, module_id)
        return lesson_id

    def get(self, lesson_id: int) -> dict | None:
        return query_one(
            "SELECT id, module_id, title, order_index FROM lessons WHERE id = %s",
            (lesson_id,),
        )

    def list_for_module(self, module_id: int) -> list[dict]:
        return query_all(
            "SELECT id, module_id, title, order_index FROM lessons "
            "WHERE module_id = %s ORDER BY order_index ASC",
            (module_id,),
        )

    def count_for_module(self, module_id: int) -> int:
        row = query_one(
            "SELECT COUNT(*) AS lesson_count FROM lessons WHERE module_id = %s",
            (module_id,),
        )
        return row["lesson_count"] if row else 0


_repository = LessonRepository()


def create_lesson(module_id: int, title: str, order_index: int) -> int:
    """Create a lesson under `module_id`, returning the new lesson id."""
    return _repository.create(module_id, title, order_index)


def get_lesson(lesson_id: int) -> dict | None:
    """Return the lesson dict (id, module_id, title, order_index) or None."""
    return _repository.get(lesson_id)


def list_lessons_for_module(module_id: int) -> list[dict]:
    """Return lessons for `module_id`, ordered by order_index ascending."""
    return _repository.list_for_module(module_id)


def count_lessons_in_module(module_id: int) -> int:
    """Return the number of lessons belonging to `module_id`."""
    return _repository.count_for_module(module_id)
