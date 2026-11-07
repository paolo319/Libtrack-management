from sqlalchemy import String, Integer
from sqlalchemy.orm import Mapped, mapped_column

from database import Base

class HeadAdmin(Base):
    __tablename__ = "head_admin"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    fullname: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    password: Mapped[str] = mapped_column(String(255), nullable=False)
