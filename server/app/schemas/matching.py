from pydantic import BaseModel
from typing import Optional
from enum import Enum


class LineVerdict(str, Enum):
    MATCH = "MATCH"
    MISMATCH = "MISMATCH"
    MISSING = "MISSING"
    EXTRA = "EXTRA"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    PARTIAL_DATA = "PARTIAL_DATA"


class GlobalVerdict(str, Enum):
    VALIDATED = "VALIDATED"
    PARTIAL = "PARTIAL"
    REJECTED = "REJECTED"
    REVIEW = "REVIEW"
    INCOMPLETE = "INCOMPLETE"


class LineComparisonResult(BaseModel):
    ref_produit: str
    designation: Optional[str] = None

    qty_bc: Optional[float] = None
    qty_bl: Optional[float] = None
    qty_facture: Optional[float] = None

    prix_bc: Optional[float] = None
    prix_facture: Optional[float] = None

    tva_bc: Optional[float] = None
    tva_facture: Optional[float] = None

    total_bc: Optional[float] = None
    total_facture: Optional[float] = None

    verdict: LineVerdict
    mismatch_fields: list[str] = []
    confidence: float = 1.0
    notes: Optional[str] = None


class MatchResultSchema(BaseModel):
    job_id: str
    global_verdict: GlobalVerdict
    line_results: list[LineComparisonResult]
    total_lines: int
    match_count: int
    mismatch_count: int
    missing_count: int
    extra_count: int
    low_confidence_count: int
    used_fuzzy_link: bool = False
    bc_to_bl_link_confidence: Optional[float] = None
    bc_to_facture_link_confidence: Optional[float] = None