"""Mentoring platform CLI (Typer).

Calls app.db.student_actions, mentor_actions and appointments, and decides how
the returned ORM objects are shown.
"""

from datetime import date, datetime, time
from typing import Annotated

import typer
from sqlalchemy.exc import SQLAlchemyError

from app.db import appointments, mentor_actions, student_actions
from app.db.appointments import APP_TZ, AppointmentError
from app.db.engine import init_db
from app.db.helpers import ServiceError
from app.db.models import MentorProfile

app = typer.Typer(no_args_is_help=True, help="Mentoring platform")
students_app = typer.Typer(no_args_is_help=True, help="Manage students")
mentors_app = typer.Typer(no_args_is_help=True, help="Manage mentors")
mentorships_app = typer.Typer(no_args_is_help=True, help="Manage appointments")
availability_app = typer.Typer(help="Manage a mentor's weekly availability.")
app.add_typer(students_app, name="students")
app.add_typer(mentors_app, name="mentors")
app.add_typer(mentorships_app, name="mentorships")
mentors_app.add_typer(availability_app, name="availability")


WEEKDAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


def subjects_of(m: MentorProfile) -> str:
    return ", ".join(sp.specialization for sp in m.specialization) or "-"


def _parse_weekday(value: str) -> int:
    key = value.strip().lower()[:3]
    if key not in WEEKDAYS:
        raise ServiceError("Weekday must be a day name like mon, tue or friday.")
    return WEEKDAYS.index(key)


def _parse_clock(value: str):
    try:
        return datetime.strptime(value.strip(), "%H:%M").time()
    except ValueError:
        raise ServiceError("Use a 24-hour time like 09:00 or 14:30.") from None


@students_app.command("list")
def students_list(limit: int | None = None) -> None:
    """List students."""
    students = student_actions.list_students(limit)
    if not students:
        typer.echo("No students found.")
    for s in students:
        role = "mentor" if s.mentor_profile is not None else "student"
        typer.echo(f"{s.student_id}  {s.name}  {s.umindanao_email}  [{role}]")


@students_app.command("add")
def students_add(
    name: str,
    student_id: Annotated[str, typer.Option(help="6-digit student ID")],
    email: str,
) -> None:
    """Add a student."""
    s = student_actions.add_student(student_id, name, email)
    typer.echo(f"Added {s.name} (student ID {s.student_id}).")


@mentors_app.command("list")
def mentors_list(status: str | None = None, subject: str | None = None) -> None:
    """List mentors, optionally filtered by --status or --subject."""
    mentors = mentor_actions.list_mentors(status, subject)
    if not mentors:
        typer.echo("No mentors found.")
    for m in mentors:
        ended = f" (ended {m.end_date})" if m.end_date is not None else ""
        typer.echo(
            f"{m.student.student_id}  {m.student.name}  {m.status}{ended}  {subjects_of(m)}"
        )


@mentors_app.command("add")
def mentors_add(student_id: str, subject: list[str] | None = None) -> None:
    """Make an existing student a mentor. Repeat --subject for several."""
    m = mentor_actions.add_mentor(student_id, subject or [])
    typer.echo(f"{m.student.name} is now a mentor. Subjects: {subjects_of(m)}")


@mentors_app.command("subjects")
def mentors_subjects(student_id: str, subjects: list[str]) -> None:
    """Replace a mentor's subjects."""
    m = mentor_actions.set_mentor_subjects(student_id, subjects)
    typer.echo(f"{m.student.name} now teaches: {subjects_of(m)}")


@mentors_app.command("retire")
def mentors_retire(student_id: str, status: str = "quit") -> None:
    """Mark a mentor as quit or graduated."""
    m = mentor_actions.retire(student_id, status)
    typer.echo(f"{m.student.name} marked as {m.status}.")


@mentorships_app.command("book")
def mentorships_book(
    mentee_id: str, mentor_id: str, subject: str, day: str, at: str
) -> None:
    """Book a one-on-one appointment. Local time, e.g.: ... Math 2026-11-20 14:00"""
    try:
        when = datetime.combine(
            date.fromisoformat(day), time.fromisoformat(at), tzinfo=APP_TZ
        )
    except ValueError:
        raise AppointmentError(
            "Use a date like 2026-11-20 and a 24-hour time like 14:00."
        ) from None
    appt = appointments.book_appointment(mentee_id, mentor_id, subject, when)
    shown = when.strftime("%a %d %b %Y, %H:%M")
    typer.echo(f"Booked appointment {appt.id}: {appt.subject} on {shown}.")


@mentorships_app.command("cancel")
def mentorships_cancel(appointment_id: int, actor_id: str) -> None:
    """Cancel a scheduled appointment. actor_id is the mentor's or student's ID."""
    appt = appointments.cancel_appointment(appointment_id, actor_id)
    typer.echo(f"Appointment {appt.id} cancelled.")


@availability_app.command("add")
def availability_add(student_id: str, weekday: str, start: str, end: str) -> None:
    """Add a weekly window (local time), e.g.: ... 202400 mon 09:00 12:00"""
    window = mentor_actions.add_availability(
        student_id, _parse_weekday(weekday), _parse_clock(start), _parse_clock(end)
    )
    typer.echo(
        f"Added window {window.id}: {WEEKDAYS[window.weekday].title()} "
        f"{window.start_time:%H:%M}-{window.end_time:%H:%M}."
    )


@availability_app.command("list")
def availability_list(student_id: str) -> None:
    """Show a mentor's availability windows."""
    windows = mentor_actions.list_availability(student_id)
    if not windows:
        typer.echo("No availability set.")
    for w in windows:
        typer.echo(
            f"{w.id}: {WEEKDAYS[w.weekday].title()} "
            f"{w.start_time:%H:%M}-{w.end_time:%H:%M}"
        )


@availability_app.command("remove")
def availability_remove(student_id: str, window_id: int) -> None:
    """Remove one window by the ID shown in `availability list`."""
    mentor_actions.remove_availability(student_id, window_id)
    typer.echo(f"Removed window {window_id}.")


def main() -> None:
    init_db()  # auto-initialize the database schema if the DB file is missing
    try:
        app()
    except (ServiceError, AppointmentError) as e:
        typer.secho(f"{type(e).__name__}: {e}", fg=typer.colors.RED, err=True)
        raise SystemExit(1)
    except SQLAlchemyError as e:
        detail = getattr(e, "orig", None) or e
        typer.secho(f"{type(e).__name__}: {detail}", fg=typer.colors.RED, err=True)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
