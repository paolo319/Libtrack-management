from datetime import datetime

from sqlalchemy import ForeignKey, TIMESTAMP, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class Visitor(Base):
    __tablename__ = "visitor"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("student.id", ondelete="CASCADE"), nullable=False, index=True
    )
    monitor_id: Mapped[int] = mapped_column(
        ForeignKey("monitor.id", ondelete="CASCADE"), nullable=False, index=True
    )
    time_in: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()"), index=True
    )

    student = relationship("Student", back_populates="visitors")
    monitor = relationship("Monitor", back_populates="visitors")
