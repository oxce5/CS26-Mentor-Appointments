import os

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from .models import Base

engine = create_engine("sqlite:///mentoring.db")
SessionLocal = sessionmaker(engine, expire_on_commit=False)


@event.listens_for(engine, "connect")
def _fk_on(dbapi_conn, _record):
    """SQLite does not support foreign_keys by default. We enable FKs on every session connect."""
    dbapi_conn.execute("PRAGMA foreign_keys = ON")  # pyright: ignore[reportUnknownMemberType]


def init_db() -> None:
    """Create the database tables if the database file doesn't exist yet."""
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    db_path = os.path.join(project_root, "mentoring.db")
    if not os.path.exists(db_path):
        Base.metadata.create_all(engine)
