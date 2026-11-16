"""Mentoring platform CLI (Typer).

Calls app.db.actions and decides how the returned ORM objects are shown.
"""

from typing import Annotated

import typer
from app.db import actions
from app.db.appointments import AppointmentError
from app.db.engine import init_db
from app.db.helpers import ServiceError
from app.db.models import MentorProfile
from sqlalchemy.exc import SQLAlchemyError

app = typer.Typer(no_args_is_help=True, help="Mentoring platform")
students_app = typer.Typer(no_args_is_help=True, help="Manage students")
mentors_app = typer.Typer(no_args_is_help=True, help="Manage mentors")
app.add_typer(students_app, name="students")
app.add_typer(mentors_app, name="mentors")


def subjects_of(m: MentorProfile) -> str:
    return ", ".join(sp.specialization for sp in m.specialization) or "-"


@students_app.command("list")
def students_list(limit: int | None = None) -> None:
    """List students."""
    students = actions.list_students(limit)
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
    s = actions.add_student(student_id, name, email)
    typer.echo(f"Added {s.name} (student ID {s.student_id}).")


@mentors_app.command("list")
def mentors_list(status: str | None = None, subject: str | None = None) -> None:
    """List mentors, optionally filtered by --status or --subject."""
    mentors = actions.list_mentors(status, subject)
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
    m = actions.add_mentor(student_id, subject or [])
    typer.echo(f"{m.student.name} is now a mentor. Subjects: {subjects_of(m)}")


@mentors_app.command("subjects")
def mentors_subjects(student_id: str, subjects: list[str]) -> None:
    """Replace a mentor's subjects."""
    m = actions.set_mentor_subjects(student_id, subjects)
    typer.echo(f"{m.student.name} now teaches: {subjects_of(m)}")


@mentors_app.command("retire")
def mentors_retire(student_id: str, status: str = "quit") -> None:
    """Mark a mentor as quit or graduated."""
    m = actions.retire(student_id, status)
    typer.echo(f"{m.student.name} marked as {m.status}.")


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
