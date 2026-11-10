from datetime import date

from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session, selectinload

from .models import *

engine = create_engine("sqlite:///mentoring.db")


@event.listens_for(engine, "connect")
def _fk_on(dbapi_conn, _record):
    dbapi_conn.execute("PRAGMA foreign_keys = ON")  # pyright: ignore[reportUnknownMemberType]


def _normalize_subjects(subjects: tuple[str, ...]) -> tuple[str, ...]:
    """Trim, title-case, de-duplicate, and sort, so 'math' and 'Math ' collapse."""
    return tuple(sorted({s.strip().title() for s in subjects if s.strip()}))


def fetch_students(session: Session, limit: int | None = None, offset: int = 0):
    stmt = select(Student).order_by(Student.id).limit(limit).offset(offset)
    return list(session.scalars(stmt))


def insert_students(session: Session, students: list[Student]) -> list[Student]:
    session.add_all(students)
    session.flush()
    return students


def update_student(
    session: Session,
    pk: int,
    *,
    name: str | None = None,
    student_id: int | None = None,
    umindanao_email: str | None = None,
) -> Student:
    student = session.get(Student, pk)
    if student is None:
        raise ValueError(f"No student with id {pk}")
    if name is not None:
        student.name = name
    if student_id is not None:
        student.student_id = student_id
    if umindanao_email is not None:
        student.umindanao_email = umindanao_email
    return student


def fetch_mentors(session: Session, limit: int | None = None, offset: int = 0):
    stmt = (
        select(MentorProfile)
        .options(
            selectinload(MentorProfile.specialization),
            selectinload(MentorProfile.student),
        )
        .order_by(MentorProfile.id)
        .limit(limit)
        .offset(offset)
    )
    return list(session.scalars(stmt))


def insert_mentors(
    session: Session, student: Student, specialization: tuple[str, ...] = ()
) -> MentorProfile:
    profile = MentorProfile(
        student=student,
        specialization=[
            MentorSpecialization(specialization=s)
            for s in _normalize_subjects(specialization)
        ],
    )
    session.add(profile)
    session.flush()
    return profile


def retire_mentor(
    session: Session, profile: MentorProfile, status: str = "quit"
) -> None:
    profile.status = status
    profile.end_date = date.today()
