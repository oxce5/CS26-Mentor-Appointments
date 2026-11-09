import os
import sqlite3
from dataclasses import dataclass, replace
from types import TracebackType
from typing import Self


@dataclass(frozen=True)
class Student:
    name: str
    student_id: int
    email: str | None = None
    id: int | None = None
    created_at: str | None = None


@dataclass(frozen=True)
class Mentor:
    name: str
    student_id: int
    email: str | None = None
    id: int | None = None
    created_at: str | None = None
    subjects: tuple[str, ...] = ()


SCHEMA = """
CREATE TABLE IF NOT EXISTS students (
    id         INTEGER PRIMARY KEY,
    student_id INTEGER NOT NULL UNIQUE,
    name       TEXT    NOT NULL,
    umindanao_email    TEXT,   NOT NULL,
    created_at TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS mentors (
    id         INTEGER PRIMARY KEY,
    student_id INTEGER NOT NULL UNIQUE,
    name       TEXT    NOT NULL,
    umindanao_email    TEXT NOT NULL,
    created_at TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS mentor_subjects (
    mentor_id INTEGER NOT NULL REFERENCES mentors(id) ON DELETE CASCADE,
    subject   TEXT    NOT NULL,
    PRIMARY KEY (mentor_id, subject)
);
"""


def _normalize_subjects(subjects: tuple[str, ...]) -> tuple[str, ...]:
    """Trim, title-case, de-duplicate, and sort, so 'math' and 'Math ' collapse."""
    return tuple(sorted({s.strip().title() for s in subjects if s.strip()}))


class DatabaseConnection:
    def __init__(self, path: str | os.PathLike[str]) -> None:
        self.db: sqlite3.Connection = sqlite3.connect(path)
        _ = self.db.execute("PRAGMA foreign_keys = ON")  # per-connection in SQLite
        _ = self.db.executescript(SCHEMA)

    # ---------- students ----------

    def fetch_students(self, limit: int = -1, offset: int = 0) -> list[Student]:
        cursor = self.db.execute(
            (
                "SELECT id, student_id, name, email, created_at "
                + "FROM students ORDER BY id LIMIT ? OFFSET ?"
            ),
            (limit, offset),
        )
        return [
            Student(
                id=i, student_id=s, name=n, email=e, created_at=c
            )  # pyright: ignore[reportAny]
            for i, s, n, e, c in cursor  # pyright: ignore[reportAny]
        ]

    def insert_students(self, students: list[Student]) -> list[Student]:
        saved: list[Student] = []
        with self.db:
            for stu in students:
                row = self.db.execute(
                    (
                        "INSERT INTO students (student_id, name, email) "
                        + "VALUES (?, ?, ?) RETURNING id, created_at"
                    ),
                    (stu.student_id, stu.name, stu.email),
                ).fetchone()
        saved.append(replace(stu, id=row[0], created_at=row[1]))
        return saved

    def update_students(self, students: list[Student]) -> None:
        rows: list[tuple[int, str, str | None, int]] = []
        for stu in students:
            if stu.id is None:
                raise ValueError(f"Cannot update unsaved student {stu.name!r}")
            rows.append((stu.student_id, stu.name, stu.email, stu.id))
        with self.db:
            _ = self.db.executemany(
                "UPDATE students SET student_id = ?, name = ?, email = ? WHERE id = ?",
                rows,
            )

    def delete_students(self, ids: list[int]) -> None:
        with self.db:
            _ = self.db.executemany(
                "DELETE FROM students WHERE id = ?", [(i,) for i in ids]
            )

    # ---------- mentors ----------

    def _subjects_for(self, mentor_ids: list[int]) -> dict[int, tuple[str, ...]]:
        if not mentor_ids:
            return {}
        marks = ",".join("?" * len(mentor_ids))  # placeholders only, no user data
        cursor = self.db.execute(
            (
                "SELECT mentor_id, subject FROM mentor_subjects "
                + f"WHERE mentor_id IN ({marks}) ORDER BY mentor_id, subject"
            ),
            mentor_ids,
        )
        grouped: dict[int, list[str]] = {}
        for mentor_id, subject in cursor:  # pyright: ignore[reportAny]
            grouped.setdefault(mentor_id, []).append(
                subject
            )  # pyright: ignore[reportAny]
        return {k: tuple(v) for k, v in grouped.items()}

    def fetch_mentors(self, limit: int = -1, offset: int = 0) -> list[Mentor]:
        rows = self.db.execute(
            (
                "SELECT id, student_id, name, email, created_at "
                + "FROM mentors ORDER BY id LIMIT ? OFFSET ?"
            ),
            (limit, offset),
        ).fetchall()
        ids: list[int] = [r[0] for r in rows]  # pyright: ignore[reportAny]
        subjects = self._subjects_for(ids)
        return [
            Mentor(
                id=i,
                student_id=s,
                name=n,
                email=e,
                created_at=c,
                subjects=subjects.get(i, ()),
            )
            for i, s, n, e, c in rows
        ]

    def insert_mentors(self, mentors: list[Mentor]) -> list[Mentor]:
        saved: list[Mentor] = []
        with self.db:
            for m in mentors:
                subjects = _normalize_subjects(m.subjects)
                row = self.db.execute(
                    (
                        "INSERT INTO mentors (student_id, name, email) "
                        + "VALUES (?, ?, ?) RETURNING id, created_at"
                    ),
                    (m.student_id, m.name, m.email),
                ).fetchone()
                _ = self.db.executemany(
                    "INSERT INTO mentor_subjects (mentor_id, subject) VALUES (?, ?)",
                    [(row[0], s) for s in subjects],
                )
                saved.append(
                    replace(m, id=row[0], created_at=row[1], subjects=subjects)
                )
        return saved

    def update_mentors(self, mentors: list[Mentor]) -> None:
        for m in mentors:
            if m.id is None:
                raise ValueError(f"Cannot update unsaved mentor {m.name!r}")
        with self.db:  # one transaction: all mentors update or none do
            for m in mentors:
                _ = self.db.execute(
                    "UPDATE mentors SET student_id = ?, name = ?, email = ? WHERE id = ?",
                    (m.student_id, m.name, m.email, m.id),
                )
                _ = self.db.execute(
                    "DELETE FROM mentor_subjects WHERE mentor_id = ?", (m.id,)
                )
                _ = self.db.executemany(
                    "INSERT INTO mentor_subjects (mentor_id, subject) VALUES (?, ?)",
                    [(m.id, s) for s in _normalize_subjects(m.subjects)],
                )

    def delete_mentors(self, ids: list[int]) -> None:
        with self.db:  # mentor_subjects rows go via ON DELETE CASCADE
            _ = self.db.executemany(
                "DELETE FROM mentors WHERE id = ?", [(i,) for i in ids]
            )

    # ---------- lifecycle ----------

    def close(self) -> None:
        self.db.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()
