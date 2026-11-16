"""Database actions. Each function opens its own session and returns the ORM objects.

Requires SessionLocal = sessionmaker(engine, expire_on_commit=False) so the returned
objects stay readable after the session closes (relationships are eager-loaded below).
"""

from app.db.models import (
    MentorProfile,
    Student,
)
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload


class ServiceError(Exception):
    """A problem the user can fix. The caller prints it as a message."""


def _normalize_subjects(subjects: list[str]) -> tuple[str, ...]:
    """Trim, title-case, de-duplicate, and sort, so 'math' and 'Math ' collapse."""
    return tuple(sorted({s.strip().title() for s in subjects if s.strip()}))


STUDENT_ID_LENGTH = 6


def clean_student_id(student_id: str) -> str:
    cleaned = student_id.strip()
    valid = cleaned.isascii() and cleaned.isdigit()
    if not valid or len(cleaned) != STUDENT_ID_LENGTH:
        raise ServiceError(f"Student ID must be exactly {STUDENT_ID_LENGTH} digits.")
    return cleaned


def find_student(session: Session, student_id: str) -> Student:
    student = session.scalar(select(Student).where(Student.student_id == student_id))
    if student is None:
        raise ServiceError(f"No student with ID {student_id}.")
    return student


def find_mentor(session: Session, student_id: str) -> MentorProfile:
    profile = session.scalar(
        select(MentorProfile)
        .join(MentorProfile.student)
        .where(Student.student_id == student_id)
        .options(
            selectinload(MentorProfile.specialization),
            selectinload(MentorProfile.student),
        )
    )
    if profile is None:
        raise ServiceError(f"No mentor with student ID {student_id}.")
    return profile


def normalize_subjects(subjects: list[str]) -> tuple[str, ...]:
    """Trim, title-case, de-duplicate, and sort, so 'math' and 'Math ' collapse."""
    return tuple(sorted({s.strip().title() for s in subjects if s.strip()}))
