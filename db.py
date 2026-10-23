import sqlite3
import os

from types import TracebackType
from typing import Self

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
        with sqlite3.connect(path) as db:
            _ = db.executescript(SCHEMA)

    def insert_users(self, users: list[str]) -> None:
        rows: list[tuple[str]] = [(n,) for n in users]
        with self.db:
            _ = self.db.executemany("INSERT INTO users (name) VALUES (?)", rows)


    def fetch_users(self, limit: int = -1, offset: int = 0) -> list[tuple[int, str]]:
        cursor = self.db.execute("SELECT id, name FROM users ORDER BY id LIMIT ? OFFSET ?", (limit, offset))
        rows: list[tuple[int, str]] = cursor.fetchall()
        return rows

    def update_users(self, users: list[str], ids: list[int]) -> None:
        rows: list[tuple[str, int]] = list(zip(users, ids, strict=True))
        with self.db:
            _ = self.db.executemany("UPDATE users SET name = ? WHERE id = ?"
, rows)

    def delete_user(self, index: list[int]) -> None:
        rows: list[tuple[int]] = [(i,) for i in index]
        with self.db:
            _ = self.db.executemany("DELETE FROM users WHERE id = ?", rows)

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
