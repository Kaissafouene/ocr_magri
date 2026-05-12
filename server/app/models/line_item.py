import uuid
from sqlalchemy import String, Float, Integer, Boolean, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.core.db_types import UUIDType, json_type


class LineItem(Base):
    __tablename__ = "line_items"

    id: Mapped[str] = mapped_column(UUIDType, primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id: Mapped[str] = mapped_column(UUIDType, ForeignKey("documents.id"), nullable=False, index=True)

    line_number: Mapped[int] = mapped_column(Integer, nullable=False)
    ref_produit: Mapped[str] = mapped_column(String(200), nullable=True, index=True)
    ref_produit_normalized: Mapped[str] = mapped_column(String(200), nullable=True)  # uppercase, stripped
    designation: Mapped[str] = mapped_column(String(1000), nullable=True)

    qty: Mapped[float] = mapped_column(Float, nullable=True)
    unit: Mapped[str] = mapped_column(String(50), nullable=True)
    prix_unitaire: Mapped[float] = mapped_column(Float, nullable=True) 
    tva_rate: Mapped[float] = mapped_column(Float, nullable=True)
    total_ligne_ht: Mapped[float] = mapped_column(Float, nullable=True)
    field_confidence_map: Mapped[dict] = mapped_column(json_type(), nullable=True)
    extraction_confidence: Mapped[float] = mapped_column(Float, default=1.0)
    has_low_confidence: Mapped[bool] = mapped_column(Boolean, default=False)

    document: Mapped["Document"] = relationship("Document", back_populates="line_items")
