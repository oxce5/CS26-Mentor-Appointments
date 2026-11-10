from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from .models import *

engine = create_engine("sqlite:///mentoring.db")
SessionLocal = sessionmaker(engine, expire_on_commit=False)


@event.listens_for(engine, "connect")
def _fk_on(dbapi_conn, _record):
    dbapi_conn.execute("PRAGMA foreign_keys = ON")  # pyright: ignore[reportUnknownMemberType]


