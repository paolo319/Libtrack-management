from datetime import datetime

from sqlalchemy import String, Integer, Enum, DateTime, ForeignKey, TIMESTAMP, text
from sqlalchemy.orm import Mapped, mapped_column

from database import Base
from models.schools import School

class Admin(Base):
    __tablename__ = "admin"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    fullname: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    password: Mapped[str] = mapped_column(String(255), nullable=False)
    school: Mapped[School] = mapped_column(Enum(School),nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=text('now()'))

