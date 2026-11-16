from datetime import date, time
from sqlite3 import IntegrityError

from app.db.engine import SessionLocal
from app.db.helpers import (
    ServiceError,
    clean_student_id,
    find_mentor,
    find_student,
    normalize_subjects,
)
from app.db.models import (
    MentorAvailability,
    MentorProfile,
    MentorSpecialization,
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


# ---------- mentors ----------


def list_mentors(
    status: str | None = None, subject: str | None = None
) -> list[MentorProfile]:
    with SessionLocal() as session:
        stmt = (
            select(MentorProfile)
            .options(
                selectinload(MentorProfile.specialization),
                selectinload(MentorProfile.student),
            )
            .order_by(MentorProfile.id)
        )
        if status is not None:
            stmt = stmt.where(MentorProfile.status == status)
        if subject is not None:
            wanted = subject.strip().title()
            stmt = stmt.where(
                MentorProfile.specialization.any(
                    MentorSpecialization.specialization == wanted
                )
            )
        return list(session.scalars(stmt))


def add_mentor(student_id: str, subjects: list[str]) -> MentorProfile:
    with SessionLocal() as session, session.begin():
        student = find_student(session, student_id)
        if student.mentor_profile is not None:
            raise ServiceError(f"{student.name} is already a mentor.")
        profile = MentorProfile(
            student=student,
            specialization=[
                MentorSpecialization(specialization=s)
                for s in normalize_subjects(subjects)
            ],
        )
        session.add(profile)
        session.flush()
        return profile


def set_mentor_subjects(student_id: str, subjects: list[str]) -> MentorProfile:
    with SessionLocal() as session, session.begin():
        profile = find_mentor(session, student_id)
        wanted = set(normalize_subjects(subjects))
        current = {row.specialization: row for row in profile.specialization}
        for name, row in current.items():
            if name not in wanted:
                profile.specialization.remove(row)  # delete-orphan removes the row
        for name in wanted - set(current):
            profile.specialization.append(MentorSpecialization(specialization=name))
        return profile


def add_availability(
    student_id: str, weekday: int, start: time, end: time
) -> MentorAvailability:
    if end <= start:
        raise ServiceError("End time must be after start time.")
    with SessionLocal() as session, session.begin():
        profile = find_mentor(session, student_id)
        for w in profile.availability:
            if w.weekday == weekday and start < w.end_time and w.start_time < end:
                raise ServiceError("That window overlaps an existing one.")
        window = MentorAvailability(weekday=weekday, start_time=start, end_time=end)
        profile.availability.append(window)
        session.flush()
        return window


def retire(student_id: str, status: str = "quit") -> MentorProfile:
    if status not in ("quit", "graduated"):
        raise ServiceError("Status must be quit or graduated.")
    with SessionLocal() as session, session.begin():
        profile = find_mentor(session, student_id)
        if profile.status != "active":
            raise ServiceError(f"{profile.student.name} is already {profile.status}.")
        profile.status = status
        profile.end_date = date.today()
        return profile
