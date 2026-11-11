from datetime import date, datetime

from sqlalchemy import Date, ForeignKey, TIMESTAMP, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class DutyRecord(Base):
    """One duty session per person per day.

    `duty_date` is the local date at time-in; the unique constraint guarantees
    a single record per duty member per day. RFID values are never stored here.
    """

    __tablename__ = "duty_record"
    __table_args__ = (
        UniqueConstraint("duty_id", "duty_date", name="uq_duty_record_day"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    duty_id: Mapped[int] = mapped_column(
        ForeignKey("duty.id", ondelete="CASCADE"), nullable=False, index=True
    )
    duty_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    time_in: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, index=True
    )
    time_out: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )

    duty = relationship("Duty", back_populates="records")
