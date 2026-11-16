from app.db.models import Base
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

engine = create_engine("sqlite:///mentoring.db")
SessionLocal = sessionmaker(engine, expire_on_commit=False)


@event.listens_for(engine, "connect")
def _fk_on(dbapi_conn, _record):
    """SQLite does not support foreign_keys by default. We enable FKs on every session connect."""
    dbapi_conn.execute("PRAGMA foreign_keys = ON")  # pyright: ignore[reportUnknownMemberType]


def init_db() -> None:
    Base.metadata.create_all(engine)
