from datetime import date, datetime, time

from sqlalchemy import CheckConstraint, ForeignKey, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Student(Base):
    __tablename__ = "student"  # pyright: ignore[reportUnannotatedClassAttribute]
    __table_args__ = (  # pyright: ignore[reportAny]
        CheckConstraint(
            "length(student_id) = 6 AND student_id NOT GLOB '*[^0-9]*'",
            name="student_id_format",
        ),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[str] = mapped_column(String(6), unique=True)
    name: Mapped[str]
    umindanao_email: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    mentor_profile: Mapped["MentorProfile | None"] = relationship(
        back_populates="student"
    )


class MentorProfile(Base):
    __tablename__ = "mentor_profile"  # pyright: ignore[reportUnannotatedClassAttribute]
    id: Mapped[int] = mapped_column(primary_key=True)
    student_pk: Mapped[int] = mapped_column(ForeignKey("student.id"), unique=True)
    status: Mapped[str] = mapped_column(default="active")
    end_date: Mapped[date | None] = mapped_column(default=None)
    student: Mapped[Student] = relationship(back_populates="mentor_profile")
    specialization: Mapped[list["MentorSpecialization"]] = relationship(
        cascade="all, delete-orphan"
    )
    availability: Mapped[list["MentorAvailability"]] = relationship(
        cascade="all, delete-orphan"
    )


class MentorSpecialization(Base):
    __tablename__ = "mentor_subject"  # pyright: ignore[reportUnannotatedClassAttribute]
    id: Mapped[int] = mapped_column(primary_key=True)
    mentor_profile_id: Mapped[int] = mapped_column(ForeignKey("mentor_profile.id"))
    specialization: Mapped[str]


class MentorAvailability(Base):
    __tablename__ = "mentor_availability"  # pyright: ignore[reportUnannotatedClassAttribute]
    __table_args__ = (
        CheckConstraint("weekday BETWEEN 0 AND 6", name="availability_weekday"),
        CheckConstraint("end_time > start_time", name="availability_time_order"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    mentor_profile_id: Mapped[int] = mapped_column(ForeignKey("mentor_profile.id"))
    weekday: Mapped[int]  # 0 = Monday, matching Python's date.weekday()
    start_time: Mapped[time]
    end_time: Mapped[time]
