from datetime import datetime

from sqlalchemy import Enum, ForeignKey, String, TIMESTAMP, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base
from models.schools import School


class Duty(Base):
    __tablename__ = "duty"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    monitor_id: Mapped[int] = mapped_column(ForeignKey("monitor.id", ondelete="CASCADE"), nullable=False, index=True)
    rfid: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    fullname: Mapped[str] = mapped_column(String(150), nullable=False)
    course: Mapped[str] = mapped_column(String(100), nullable=False)
    year_level: Mapped[str] = mapped_column(String(50), nullable=False)
    school: Mapped[School] = mapped_column(Enum(School), nullable=False, index=True)
    time_in: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=text("now()"), nullable=False, index=True)
    time_out: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    monitor = relationship("Monitor", back_populates="duties")