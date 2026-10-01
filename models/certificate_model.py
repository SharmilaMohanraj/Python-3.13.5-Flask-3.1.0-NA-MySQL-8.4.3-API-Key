"""Certificate data access.

A certificate is issued at most once per (student, course) pair — enforced
by schema.sql's `uq_certificates_student_course` unique constraint and,
here, by an idempotent upsert. Certificates are only ever created by
`models.progress_model`'s cascade-completion logic, once a student finishes
every lesson in every module of a course, and are never revoked once
issued.
"""
import logging

from db import execute, query_all, query_one

logger = logging.getLogger(__name__)

_COLUMNS = "id, student_id, course_id, issued_at"


class CertificateRepository:
    """Encapsulates all SQL for the `certificates` table."""

    def find(self, student_id: int, course_id: int) -> dict | None:
        return query_one(
            f"SELECT {_COLUMNS} FROM certificates WHERE student_id = %s AND course_id = %s",
            (student_id, course_id),
        )

    def insert(self, student_id: int, course_id: int) -> int:
        return execute(
            "INSERT INTO certificates (student_id, course_id, issued_at) VALUES (%s, %s, NOW())",
            (student_id, course_id),
        )

    def list_for_student(self, student_id: int) -> list[dict]:
        return query_all(
            f"SELECT {_COLUMNS} FROM certificates WHERE student_id = %s ORDER BY issued_at DESC",
            (student_id,),
        )


_repository = CertificateRepository()


def create_certificate(student_id: int, course_id: int) -> int:
    """Idempotently issue a certificate for a (student, course) pair.

    If one already exists, its id is returned without inserting a
    duplicate. Called exclusively by
    `models.progress_model.upsert_lesson_progress`'s completion cascade.
    """
    existing = _repository.find(student_id, course_id)
    if existing is not None:
        return existing["id"]

    certificate_id = _repository.insert(student_id, course_id)
    logger.info("Certificate issued: student_id=%s course_id=%s certificate_id=%s", student_id, course_id, certificate_id)
    return certificate_id


def get_certificate(student_id: int, course_id: int) -> dict | None:
    """Return the certificate for a (student, course) pair, or None if not yet issued."""
    return _repository.find(student_id, course_id)


def list_certificates_for_student(student_id: int) -> list[dict]:
    """Return every certificate earned by `student_id`, most recently issued first."""
    return _repository.list_for_student(student_id)
