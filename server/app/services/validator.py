from decimal import Decimal
from datetime import date
from pydantic import ValidationError
from app.schemas.documents import (
    BonDeCommandeSchema, BonDeLivraison, FactureSchema,
    LineItemSchema, DocumentType
)
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


LINE_TOTAL_TOLERANCE = Decimal(str(settings.line_total_tolerance))
PRICE_TOLERANCE = Decimal(str(settings.price_tolerance))


class ValidationResult:
    def __init__(self):
        self.is_valid: bool = True
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.field_flags: dict[str, str] = {}  # field_name → "ERROR" | "WARNING"

    def add_error(self, field: str, message: str):
        self.is_valid = False
        self.errors.append(f"{field}: {message}")
        self.field_flags[field] = "ERROR"

    def add_warning(self, field: str, message: str):
        self.warnings.append(f"{field}: {message}")
        self.field_flags[field] = "WARNING"


def validate_bc(bc: BonDeCommandeSchema) -> ValidationResult:
    result = ValidationResult()
    if not bc.ref_bc:
        result.add_error("ref_bc", "Document reference is missing")
    if not bc.document_date:
        result.add_warning("document_date", "Date not extracted")
    if not bc.lines:
        result.add_error("lines", "No line items extracted")
        return result
    for i, line in enumerate(bc.lines):
        line_label = f"line[{i}]"
        if not line.ref_produit:
            result.add_warning(f"{line_label}.ref_produit", "Product reference missing")
        if line.qty is None or line.qty <= 0:
            result.add_error(f"{line_label}.qty", f"Invalid quantity: {line.qty}")
        if line.prix_unitaire is None or line.prix_unitaire <= 0:
            result.add_warning(f"{line_label}.prix_unitaire", "Unit price missing")
        if line.qty and line.prix_unitaire and line.total_ligne_ht:
            expected = line.qty * line.prix_unitaire
            diff = abs(expected - line.total_ligne_ht)
            if diff > LINE_TOTAL_TOLERANCE:
                result.add_warning(
                    f"{line_label}.total_ligne_ht",
                    f"Math mismatch: {line.qty} × {line.prix_unitaire} = {expected} ≠ {line.total_ligne_ht} (diff={diff})"
                )

    return result


def validate_bl(bl: BonDeLivraison) -> ValidationResult:
    result = ValidationResult()

    if not bl.ref_bl:
        result.add_error("ref_bl", "BL reference is missing")
    if not bl.document_date:
        result.add_warning("document_date", "Date not extracted")
    if not bl.lines:
        result.add_error("lines", "No line items extracted")
        return result

    for i, line in enumerate(bl.lines):
        line_label = f"line[{i}]"
        if not line.ref_produit:
            result.add_warning(f"{line_label}.ref_produit", "Product reference missing")
        if line.qty is None or line.qty <= 0:
            result.add_error(f"{line_label}.qty", f"Invalid quantity: {line.qty}")

    return result


def validate_facture(facture: FactureSchema) -> ValidationResult:
    result = ValidationResult()

    if not facture.ref_facture:
        result.add_error("ref_facture", "Invoice reference is missing")
    if not facture.document_date:
        result.add_warning("document_date", "Date not extracted")
    if not facture.lines:
        result.add_error("lines", "No line items extracted")
        return result
    if facture.total_ht and facture.lines:
        computed_ht = sum(
            ln.total_ligne_ht for ln in facture.lines if ln.total_ligne_ht
        )
        if computed_ht > 0:
            diff = abs(computed_ht - facture.total_ht)
            if diff > Decimal("0.10"):
                result.add_warning(
                    "total_ht",
                    f"Sum of lines ({computed_ht}) ≠ stated total HT ({facture.total_ht})"
                )
    if facture.total_ht and facture.total_ttc and facture.tva_rate:
        expected_ttc = facture.total_ht * (1 + facture.tva_rate / 100)
        diff = abs(expected_ttc - facture.total_ttc)
        if diff > Decimal("0.10"):
            result.add_warning(
                "total_ttc",
                f"TVA math: {facture.total_ht} × (1 + {facture.tva_rate}/100) = {expected_ttc} ≠ {facture.total_ttc}"
            )

    for i, line in enumerate(facture.lines):
        line_label = f"line[{i}]"
        if not line.ref_produit:
            result.add_warning(f"{line_label}.ref_produit", "Product reference missing")
        if line.qty is None or line.qty <= 0:
            result.add_error(f"{line_label}.qty", f"Invalid quantity: {line.qty}")
        if line.prix_unitaire is None or line.prix_unitaire <= 0:
            result.add_error(f"{line_label}.prix_unitaire", "Unit price missing on invoice line")

    return result


def validate_date_ordering(
    bc: BonDeCommandeSchema,
    bl: BonDeLivraison | None,
    facture: FactureSchema | None,
) -> list[str]:
    """
    Cross-document temporal validation.
    BL date must be >= BC date.
    FACTURE date must be >= BL date (if BL present).
    Returns list of warning strings.
    """
    warnings = []

    if bc.document_date and bl and bl.document_date:
        if bl.document_date < bc.document_date:
            warnings.append(
                f"BL date ({bl.document_date}) is before BC date ({bc.document_date})"
            )

    if bl and bl.document_date and facture and facture.document_date:
        if facture.document_date < bl.document_date:
            warnings.append(
                f"FACTURE date ({facture.document_date}) is before BL date ({bl.document_date})"
            )
    elif bc.document_date and facture and facture.document_date:
        if facture.document_date < bc.document_date:
            warnings.append(
                f"FACTURE date ({facture.document_date}) is before BC date ({bc.document_date})"
            )

    return warnings