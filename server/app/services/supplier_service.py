from dataclasses import dataclass, field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.supplier_profile import SupplierProfile as SupplierProfileModel
from app.core.logging import get_logger
import re

logger = get_logger(__name__)


@dataclass
class SupplierProfile:
    id: str
    name: str
    field_aliases: dict = field(default_factory=dict)
    number_locale: str = "fr"
    date_format: str = "%d/%m/%Y"
    price_tolerance: float | None = None
    quantity_tolerance: float | None = None


async def get_supplier_from_text(header_text: str, db: AsyncSession) -> SupplierProfile | None:
    """
    Try to identify the supplier from the document header.
    Matches against name, SIRET, VAT number, and name aliases.
    """
    result = await db.execute(select(SupplierProfileModel).where(SupplierProfileModel.is_confirmed == True))
    all_suppliers = result.scalars().all()

    header_upper = header_text.upper()

    for supplier in all_suppliers:
        # Check primary name
        if supplier.name.upper() in header_upper:
            logger.info("supplier_detected", supplier=supplier.name, method="name_match")
            return _to_dataclass(supplier)

        # Check SIRET
        if supplier.siret and supplier.siret in header_text:
            logger.info("supplier_detected", supplier=supplier.name, method="siret_match")
            return _to_dataclass(supplier)

        # Check VAT
        if supplier.vat_number and supplier.vat_number in header_text:
            logger.info("supplier_detected", supplier=supplier.name, method="vat_match")
            return _to_dataclass(supplier)

        # Check aliases
        for alias in (supplier.name_aliases or []):
            if alias.upper() in header_upper:
                logger.info("supplier_detected", supplier=supplier.name, method="alias_match", alias=alias)
                return _to_dataclass(supplier)

    logger.info("supplier_not_detected", header_preview=header_text[:100])
    return None


def _to_dataclass(model: SupplierProfileModel) -> SupplierProfile:
    return SupplierProfile(
        id=model.id,
        name=model.name,
        field_aliases=model.field_aliases or {},
        number_locale=model.number_locale or "fr",
        date_format=model.date_format or "%d/%m/%Y",
        price_tolerance=model.price_tolerance,
        quantity_tolerance=model.quantity_tolerance,
    )