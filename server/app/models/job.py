import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Integer, Enum as SAEnum, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum
from app.core.database import Base
from app.core.db_types import UUIDType


class JobStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    CLASSIFYING = "CLASSIFYING"
    EXTRACTING = "EXTRACTING"
    VALIDATING = "VALIDATING"
    MATCHING = "MATCHING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"


class GlobalVerdict(str, enum.Enum):
    VALIDATED = "VALIDATED"
    PARTIAL = "PARTIAL"
    REJECTED = "REJECTED"
    REVIEW = "REVIEW"
    INCOMPLETE = "INCOMPLETE"
    PENDING = "PENDING"


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(
        UUIDType,
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    status: Mapped[JobStatus] = mapped_column(
        SAEnum(JobStatus), default=JobStatus.PENDING, nullable=False, index=True
    )
    verdict: Mapped[GlobalVerdict] = mapped_column(
        SAEnum(GlobalVerdict), default=GlobalVerdict.PENDING, nullable=True
    )

    original_pdf_key: Mapped[str] = mapped_column(String(500), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    original_pdf_hash: Mapped[str] = mapped_column(String(64), nullable=True)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    page_count: Mapped[int] = mapped_column(Integer, nullable=True)
    uploaded_by: Mapped[str] = mapped_column(String(255), nullable=True)
    error_message: Mapped[str] = mapped_column(String(2000), nullable=True)
    processing_started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    processing_completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    documents: Mapped[list["Document"]] = relationship(
        "Document", back_populates="job", cascade="all, delete-orphan"
    )
    match_result: Mapped["MatchResult"] = relationship(
        "MatchResult", back_populates="job", uselist=False, cascade="all, delete-orphan"
    )
    audit_logs: Mapped[list["AuditLog"]] = relationship(
        "AuditLog", back_populates="job", cascade="all, delete-orphan"
    )
