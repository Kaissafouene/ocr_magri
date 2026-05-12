import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.core.db_types import UUIDType, json_type


class SupplierProfile(Base):
    __tablename__ = "supplier_profiles"

    id: Mapped[str] = mapped_column(UUIDType, primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(500), nullable=False, unique=True, index=True)
    siret: Mapped[str] = mapped_column(String(14), nullable=True, unique=True, index=True)
    vat_number: Mapped[str] = mapped_column(String(50), nullable=True)
    name_aliases: Mapped[list] = mapped_column(json_type(), default=list)
    field_aliases: Mapped[dict] = mapped_column(json_type(), default=dict)

    # Number format: "fr" (1 200,50) or "en" (1,200.50) or "bare" (1200.50)
    number_locale: Mapped[str] = mapped_column(String(10), default="fr")

    # Date format string: "%d/%m/%Y" 
    date_format: Mapped[str] = mapped_column(String(30), default="%d/%m/%Y")
    price_tolerance: Mapped[float] = mapped_column(nullable=True)
    quantity_tolerance: Mapped[float] = mapped_column(nullable=True)
    is_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    confirmed_by: Mapped[str] = mapped_column(String(255), nullable=True)
    confirmed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    documents: Mapped[list["Document"]] = relationship("Document", back_populates="supplier")
