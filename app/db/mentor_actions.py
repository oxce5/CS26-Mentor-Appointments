from datetime import date, time

from app.db.engine import SessionLocal
from app.db.helpers import (
    ServiceError,
    find_mentor,
    find_student,
    normalize_subjects,
)
from app.db.models import (
    MentorAvailability,
    MentorProfile,
    MentorSpecialization,
)
from sqlalchemy import select
from sqlalchemy.orm import selectinload


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


def list_availability(student_id: str) -> list[MentorAvailability]:
    with SessionLocal() as session:
        profile = find_mentor(session, student_id)
        return sorted(profile.availability, key=lambda w: (w.weekday, w.start_time))


def remove_availability(student_id: str, window_id: int) -> None:
    with SessionLocal() as session, session.begin():
        profile = find_mentor(session, student_id)
        window = next((w for w in profile.availability if w.id == window_id), None)
        if window is None:
            raise ServiceError(f"No availability window {window_id} for this mentor.")
        profile.availability.remove(window)  # delete-orphan removes the row


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
