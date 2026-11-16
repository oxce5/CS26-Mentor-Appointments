from sqlite3 import IntegrityError

from app.db.engine import SessionLocal
from app.db.helpers import (
    ServiceError,
    clean_student_id,
    find_student,
)
from app.db.models import (
    Student,
)
from sqlalchemy import select
from sqlalchemy.orm import selectinload


def list_students(limit: int | None = None) -> list[Student]:
    with SessionLocal() as session:
        stmt = (
            select(Student)
            .options(selectinload(Student.mentor_profile))
            .order_by(Student.id)
            .limit(limit)
        )
        return list(session.scalars(stmt))


def add_student(student_id: str, name: str, email: str) -> Student:
    if not name.strip() or not email.strip():
        raise ServiceError("Name and email cannot be blank.")
    student_id = clean_student_id(student_id)
    try:
        with SessionLocal() as session, session.begin():
            student = Student(
                student_id=student_id, name=name.strip(), umindanao_email=email.strip()
            )
            session.add(student)
            session.flush()
            return student
    except IntegrityError:
        raise ServiceError(f"Student ID {student_id} is already in use.") from None


def update_student(
    student_id: str, *, name: str | None = None, email: str | None = None
) -> Student:
    with SessionLocal() as session, session.begin():
        student = find_student(session, student_id)
        if name is not None:
            student.name = name.strip()
        if email is not None:
            student.umindanao_email = email.strip()
        return student
