import uuid
from datetime import datetime
from sqlalchemy import String, Float, Boolean, ForeignKey, Enum as SAEnum, func, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum
from app.core.database import Base
from app.core.db_types import UUIDType, json_type


class LineVerdict(str, enum.Enum):
    MATCH = "MATCH"
    MISMATCH = "MISMATCH"
    MISSING = "MISSING"
    EXTRA = "EXTRA"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    PARTIAL_DATA = "PARTIAL_DATA"


class GlobalVerdict(str, enum.Enum):
    VALIDATED = "VALIDATED"
    PARTIAL = "PARTIAL"
    REJECTED = "REJECTED"
    REVIEW = "REVIEW"
    INCOMPLETE = "INCOMPLETE"


class MatchResult(Base):
    __tablename__ = "match_results"

    id: Mapped[str] = mapped_column(UUIDType, primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id: Mapped[str] = mapped_column(UUIDType, ForeignKey("jobs.id"), nullable=False, unique=True, index=True)

    global_verdict: Mapped[GlobalVerdict] = mapped_column(SAEnum(GlobalVerdict), nullable=False)
    bc_to_bl_link_confidence: Mapped[float] = mapped_column(Float, nullable=True)
    bc_to_facture_link_confidence: Mapped[float] = mapped_column(Float, nullable=True)
    used_fuzzy_link: Mapped[bool] = mapped_column(Boolean, default=False)
    total_lines: Mapped[int] = mapped_column(default=0)
    match_count: Mapped[int] = mapped_column(default=0)
    mismatch_count: Mapped[int] = mapped_column(default=0)
    missing_count: Mapped[int] = mapped_column(default=0)
    extra_count: Mapped[int] = mapped_column(default=0)
    low_confidence_count: Mapped[int] = mapped_column(default=0)
    line_verdicts: Mapped[list] = mapped_column(json_type(), nullable=False, default=list)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    job: Mapped["Job"] = relationship("Job", back_populates="match_result")
