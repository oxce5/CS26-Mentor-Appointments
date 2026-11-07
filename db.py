import sqlite3
import os

from types import TracebackType
from typing import Self

from dataclasses import dataclass, replace
@dataclass(frozen=True)
class User:
    name: str
    id: int | None = None
    created_at: str | None = None

class DatabaseConnection:
    def __init__(self, path: str | os.PathLike[str]) -> None:
        self.db: sqlite3.Connection = sqlite3.connect(path)
        SCHEMA = """
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
                """
        _ = self.db.executescript(SCHEMA)

    def fetch_users(self, limit: int = -1, offset: int = 0) -> list[User]:
        cursor = self.db.execute(
            "SELECT id, name, created_at FROM users ORDER BY id LIMIT ? OFFSET ?",
            (limit, offset),
        )

        return [User(id=i, name=n, created_at=c) for i, n, c in cursor]

    def insert_users(self, user: list[User]) -> list[User]:
        saved: list[User] = []
        with self.db:
            for usr in user:
                cursor = self.db.execute("INSERT INTO users (name) VALUES (?)", (usr.name,))
                saved.append(replace(usr, id=cursor.lastrowid))
        return saved

    def update_users(self, users: list[User]) -> None:
        rows: list[tuple[str,int]] = []
        with self.db:
            for user in users:
                if user.id is None:
                    raise ValueError(f"Cannot update unsaved user {user.id!r}")
                rows.append((user.name, user.id))
            with self.db:
                _ = self.db.executemany("UPDATE users SET name = ? WHERE id = ?", rows)

    def delete_user(self, ids: list[int]) -> None:
        with self.db:
            _ = self.db.executemany("DELETE FROM users WHERE id = ?", [(i,) for i in ids])

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
