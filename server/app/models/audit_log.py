import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, func, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.core.db_types import UUIDType, json_type


class AuditLog(Base):
    """
    Immutable append-only log.
    Application DB user has INSERT only on this table — enforced at DB level.
    Every decision the system makes is recorded here.
    """
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(UUIDType, primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id: Mapped[str] = mapped_column(UUIDType, ForeignKey("jobs.id"), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    event_data: Mapped[dict] = mapped_column(json_type(), nullable=False)
    actor: Mapped[str] = mapped_column(String(255), nullable=False, default="system")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    job: Mapped["Job"] = relationship("Job", back_populates="audit_logs")
