from pathlib import Path

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base

LOGOS_DIR = Path(__file__).resolve().parent.parent / "static" / "logos"
DEFAULT_LOGO = "default.svg"
LOGO_EXTENSIONS = (".png", ".jpg", ".jpeg", ".svg", ".webp")


class School(Base):
    __tablename__ = "schools"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    logo_filename: Mapped[str | None] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true")

    admins = relationship("Admin", back_populates="school")
    monitors = relationship("Monitor", back_populates="school")
    students = relationship("Student", back_populates="school")
    duties = relationship("Duty", back_populates="school")

    @property
    def logo_url(self) -> str:
        base = self.code.lower()
        candidates = []
        if self.logo_filename:
            candidates.append(self.logo_filename)
            
        candidates.append(f"{base}.png")
        candidates.extend(f"{base}{ext}" for ext in LOGO_EXTENSIONS)

        available = {}
        if LOGOS_DIR.is_dir():
            available = {
                path.name.lower(): path.name
                for path in LOGOS_DIR.iterdir()
                if path.is_file()
            }

        for name in candidates:
            actual = available.get(name.lower())
            if actual:
                return f"/static/logos/{actual}"
        return f"/static/logos/{DEFAULT_LOGO}"


# --- Enum version (kept for reference, not active) ---
# from enum import Enum as PyEnum
#
# class School(str, PyEnum):
#     ILOILO = "University of Iloilo"
#     ARAULLO = "Araullo University"
#     UPANG = "University of Pangasinan"
#     STJUDE = "Saint Jude College"
#     RIZALLAGUNA = "Rizal College of Laguna"
#     COC = "Cagayan De Oro College"
