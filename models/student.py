from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base
from models.schools import School


class Student(Base):
    __tablename__ = "student"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    fullname: Mapped[str] = mapped_column(String, nullable=False)
    school_id: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    course: Mapped[str] = mapped_column(String, nullable=False)
    year_level: Mapped[str] = mapped_column(String, nullable=False)
    institution_id: Mapped[int] = mapped_column(
        ForeignKey("schools.id"), nullable=False, index=True
    )
    visitors = relationship("Visitor", back_populates="student")
    school: Mapped[School] = relationship("School", back_populates="students")
