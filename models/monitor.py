from datetime import datetime
from sqlalchemy import String, Integer, ForeignKey, TIMESTAMP, text, Enum
from sqlalchemy.orm import Mapped, mapped_column
from database import Base
from models.schools import School

class Monitor(Base):
    __tablename__ = "monitor"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    admin_id: Mapped[int] = mapped_column(Integer, ForeignKey("admin.id", ondelete="CASCADE"))
    school: Mapped[School] = mapped_column(Enum(School),nullable=False)
    area: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    password: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=text('now()'))

    
