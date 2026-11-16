from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from app.db.engine import SessionLocal
from app.db.helpers import clean_student_id, find_mentor, find_student
from app.db.models import (
    Appointment,
)
from sqlalchemy import select

APP_TZ = ZoneInfo("Asia/Manila")  # availability windows are in this zone


class AppointmentError(Exception):
    """A problem raised while trying to book an appointment."""


def book_appointment(
    mentee_student_id: str,
    mentor_student_id: str,
    subject: str,
    scheduled_at: datetime,
) -> Appointment:
    if scheduled_at.tzinfo is None:
        raise AppointmentError("The appointment time must include a time zone.")
    when_utc = scheduled_at.astimezone(UTC)
    if when_utc <= datetime.now(UTC):
        raise AppointmentError("Appointments must be in the future.")
    when_db = when_utc.replace(tzinfo=None)  # SQLite stores naive UTC

    subject = subject.strip().title()

    with SessionLocal() as session, session.begin():
        mentee = find_student(session, clean_student_id(mentee_student_id))
        mentor = find_mentor(session, clean_student_id(mentor_student_id))

        if mentor.student.id == mentee.id:
            raise AppointmentError("You can't book an appointment with yourself.")
        if mentor.status != "active":
            raise AppointmentError(
                f"{mentor.student.name} is no longer an active mentor."
            )
        if subject not in {s.specialization for s in mentor.specialization}:
            raise AppointmentError(f"{mentor.student.name} doesn't teach {subject}.")

        # TODO: check the mentor's weekly availability here once it is added.

        # Double-booking: exact start time only (duration is still parked).
        clash = session.scalar(
            select(Appointment.id).where(
                Appointment.scheduled_at == when_db,
                Appointment.status == "scheduled",
                (Appointment.mentor_id == mentor.id)
                | (Appointment.student_id == mentee.id),
            )
        )
        if clash is not None:
            raise AppointmentError(
                "Either you or the mentor already has a session then."
            )

        appointment = Appointment(
            mentor_id=mentor.id,
            student_id=mentee.id,
            subject=subject,
            scheduled_at=when_db,
            status="scheduled",
        )
        session.add(appointment)
        session.flush()
        return appointment


def cancel_appointment(appointment_id: int, student_id: str):
    student_id = clean_student_id(student_id)
    with SessionLocal() as session, session.begin():
        appointment = session.get(Appointment, appointment_id)
        if appointment is None:
            raise AppointmentError("Appointment not found.")

        actor = find_student(session, student_id)
        participants = {appointment.student_id, appointment.mentor.student.id}
        if actor.id not in participants:
            raise AppointmentError(
                "Only the mentor or the student can cancel this appointment."
            )

        if appointment.status != "scheduled":
            raise AppointmentError(
                f"Only scheduled appointments can be cancelled (this one is {appointment.status})."
            )
        if appointment.scheduled_at <= datetime.now(UTC).replace(tzinfo=None):
            raise AppointmentError(
                "That appointment has already started. Mark it attended or absent instead."
            )

        appointment.status = "cancelled"
        return appointment
