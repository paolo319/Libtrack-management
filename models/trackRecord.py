from datetime import datetime

from sqlalchemy import ForeignKey, TIMESTAMP, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class TrackRecord(Base):
    __tablename__ = "track_record"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    visitor_id: Mapped[int] = mapped_column(
        ForeignKey("visitor.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    duty_record_id: Mapped[int] = mapped_column(
        ForeignKey("duty_record.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    date_enter: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=text("now()"),
        index=True
    )

    visitor = relationship("Visitor", back_populates="track_records")
    duty_record = relationship("DutyRecord", back_populates="track_records")