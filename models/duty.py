from pathlib import Path

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base
from models.schools import School

# Duty personnel photos live in static/pp, not static/logos.
PP_DIR = Path(__file__).resolve().parent.parent / "static" / "pp"
DEFAULT_LOGO = "bow-kratos.gif"
LOGO_EXTENSIONS = (".png", ".jpg", ".jpeg", ".svg", ".webp", ".gif")


class Duty(Base):
    __tablename__ = "duty"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    monitor_id: Mapped[int] = mapped_column(
        ForeignKey("monitor.id", ondelete="CASCADE"), nullable=False, index=True
    )
    school_id: Mapped[int] = mapped_column(
        ForeignKey("schools.id"), nullable=False, index=True
    )
    logo_filename: Mapped[str | None] = mapped_column(String(255))
    rfid: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    fullname: Mapped[str] = mapped_column(String(150), nullable=False)
    course: Mapped[str] = mapped_column(String(100), nullable=False)
    year_level: Mapped[str] = mapped_column(String(50), nullable=False)
    monitor = relationship("Monitor", back_populates="duties")
    school: Mapped[School] = relationship("School", back_populates="duties")
    records = relationship(
        "DutyRecord",
        back_populates="duty",
        cascade="all, delete-orphan",
        order_by="DutyRecord.time_in",
    )

    @property
    def logo_url(self) -> str:
        available = {}
        if PP_DIR.is_dir():
            available = {
                path.name.lower(): path.name
                for path in PP_DIR.iterdir()
                if path.is_file()
            }

        if self.logo_filename:
            base = Path(self.logo_filename).name
            for suffix in ("", *LOGO_EXTENSIONS):
                actual = available.get(f"{base}{suffix}".lower())
                if actual:
                    return f"/static/pp/{actual}"
        return f"/static/pp/{DEFAULT_LOGO}"
