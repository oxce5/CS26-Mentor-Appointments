from datetime import datetime

from sqlalchemy import ForeignKey, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Student(Base):
    __tablename__ = "student"  # pyright: ignore[reportUnannotatedClassAttribute]
    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(unique=True)
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
    student: Mapped[Student] = relationship(back_populates="mentor_profile")
    specialization: Mapped[list["MentorSpecialization"]] = relationship(
        cascade="all, delete-orphan"
    )


class MentorSpecialization(Base):
    __tablename__ = "mentor_subject"  # pyright: ignore[reportUnannotatedClassAttribute]
    id: Mapped[int] = mapped_column(primary_key=True)
    mentor_profile_id: Mapped[int] = mapped_column(ForeignKey("mentor_profile.id"))
    specialization: Mapped[str]
