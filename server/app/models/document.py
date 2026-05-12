import uuid
from datetime import datetime, date
from sqlalchemy import String, DateTime, Date, Float, Integer, Boolean, ForeignKey, Enum as SAEnum, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum
from app.core.database import Base
from app.core.db_types import UUIDType, json_type


class DocumentType(str, enum.Enum):
    BC = "BC"
    BL = "BL"
    FACTURE = "FACTURE"
    UNKNOWN = "UNKNOWN"


class ExtractionSourceTier(int, enum.Enum):
    TEMPLATE = 1    # rule-based template
    CLOUD_OCR = 2   # Google Document AI
    LLM = 3         # OpenAI fallback
    HUMAN = 4       # manually corrected


class PageSourceType(str, enum.Enum):
    NATIVE = "NATIVE"    # PDF has text layer
    SCANNED = "SCANNED"  # image-based PDF


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(UUIDType, primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id: Mapped[str] = mapped_column(UUIDType, ForeignKey("jobs.id"), nullable=False, index=True)

    doc_type: Mapped[DocumentType] = mapped_column(SAEnum(DocumentType), nullable=False)
    page_numbers: Mapped[list] = mapped_column(json_type(), nullable=False, default=list)  # [1, 2] for multi-page
    page_source_type: Mapped[PageSourceType] = mapped_column(SAEnum(PageSourceType), nullable=True)
    classification_confidence: Mapped[float] = mapped_column(Float, nullable=True)
    classification_source_tier: Mapped[int] = mapped_column(Integer, nullable=True)  # 1, 2, 3
    extraction_source_tier: Mapped[ExtractionSourceTier] = mapped_column(
        SAEnum(ExtractionSourceTier), nullable=True
    )
    extraction_confidence: Mapped[float] = mapped_column(Float, nullable=True)
    has_low_confidence_fields: Mapped[bool] = mapped_column(Boolean, default=False)
    supplier_id: Mapped[str] = mapped_column(
        UUIDType, ForeignKey("supplier_profiles.id"), nullable=True
    )
    supplier_name_raw: Mapped[str] = mapped_column(String(500), nullable=True)
    ref_document: Mapped[str] = mapped_column(String(100), nullable=True, index=True)
    ref_bc_linked: Mapped[str] = mapped_column(String(100), nullable=True)  #link back 
    document_date: Mapped[date] = mapped_column(Date, nullable=True)
    total_ht: Mapped[float] = mapped_column(Float, nullable=True)
    total_tva: Mapped[float] = mapped_column(Float, nullable=True)
    total_ttc: Mapped[float] = mapped_column(Float, nullable=True)
    tva_rate: Mapped[float] = mapped_column(Float, nullable=True)

    raw_extracted_data: Mapped[dict] = mapped_column(json_type(), nullable=True)
    field_confidence_map: Mapped[dict] = mapped_column(json_type(), nullable=True)
    requires_review: Mapped[bool] = mapped_column(Boolean, default=False)
    reviewed_by: Mapped[str] = mapped_column(String(255), nullable=True)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    job: Mapped["Job"] = relationship("Job", back_populates="documents")
    line_items: Mapped[list["LineItem"]] = relationship(
        "LineItem", back_populates="document", cascade="all, delete-orphan"
    )
    supplier: Mapped["SupplierProfile"] = relationship("SupplierProfile", back_populates="documents")
