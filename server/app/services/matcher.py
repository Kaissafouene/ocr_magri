"""
3-Way Matching Engine — 100% deterministic. Zero AI. Zero ML.
Compares BC ↔ BL ↔ FACTURE line by line.
"""
from decimal import Decimal
from dataclasses import dataclass, field
from app.schemas.documents import (
    BonDeCommandeSchema, BonDeLivraison, FactureSchema, LineItemSchema
)
from app.schemas.matching import (
    LineVerdict, GlobalVerdict, LineComparisonResult, MatchResultSchema
)
from app.utils.fuzzy import refs_match_exact, refs_match_fuzzy, product_refs_match
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class MatchContext:
    job_id: str
    price_tolerance: Decimal = field(default_factory=lambda: Decimal(str(settings.price_tolerance)))
    qty_tolerance: Decimal = field(default_factory=lambda: Decimal(str(settings.quantity_tolerance)))
    tva_tolerance: Decimal = field(default_factory=lambda: Decimal(str(settings.tva_tolerance)))
    line_total_tolerance: Decimal = field(default_factory=lambda: Decimal(str(settings.line_total_tolerance)))


def _decimal(val) -> Decimal | None:
    if val is None:
        return None
    try:
        return Decimal(str(val))
    except Exception:
        return None


def _within_tolerance(a: Decimal | None, b: Decimal | None, tolerance: Decimal) -> bool:
    """Pure numeric comparison with tolerance. None values never match."""
    if a is None or b is None:
        return False
    return abs(a - b) <= tolerance


def link_documents(
    bc: BonDeCommandeSchema,
    bl: BonDeLivraison | None,
    facture: FactureSchema | None,
    ctx: MatchContext,
) -> dict:
    """
    Verify document links via reference numbers.
    Returns: { bc_bl_linked, bc_facture_linked, bc_bl_confidence, bc_facture_confidence, used_fuzzy }
    """
    result = {
        "bc_bl_linked": False,
        "bc_facture_linked": False,
        "bc_bl_confidence": None,
        "bc_facture_confidence": None,
        "used_fuzzy": False,
        "link_warnings": [],
    }

    # BC ↔ BL linking
    if bl:
        if bl.ref_bc_linked:
            if refs_match_exact(bc.ref_bc, bl.ref_bc_linked):
                result["bc_bl_linked"] = True
                result["bc_bl_confidence"] = 1.0
            else:
                matched, conf = refs_match_fuzzy(
                    bc.ref_bc,
                    bl.ref_bc_linked,
                    settings.reference_levenshtein_max_distance
                )
                if matched:
                    result["bc_bl_linked"] = True
                    result["bc_bl_confidence"] = conf
                    result["used_fuzzy"] = True
                    result["link_warnings"].append(
                        f"BC-BL fuzzy link used: '{bc.ref_bc}' ≈ '{bl.ref_bc_linked}' (confidence={conf:.2f})"
                    )
                else:
                    result["link_warnings"].append(
                        f"BC ref '{bc.ref_bc}' does not match BL's linked ref '{bl.ref_bc_linked}'"
                    )
        else:
            # BL has no ref_bc — mark as linked with lower confidence (common for some suppliers)
            result["bc_bl_linked"] = True
            result["bc_bl_confidence"] = 0.70
            result["link_warnings"].append("BL has no ref_bc_linked — link assumed by document position")

    # BC ↔ FACTURE linking
    if facture:
        if facture.ref_bc_linked:
            if refs_match_exact(bc.ref_bc, facture.ref_bc_linked):
                result["bc_facture_linked"] = True
                result["bc_facture_confidence"] = 1.0
            else:
                matched, conf = refs_match_fuzzy(
                    bc.ref_bc,
                    facture.ref_bc_linked,
                    settings.reference_levenshtein_max_distance
                )
                if matched:
                    result["bc_facture_linked"] = True
                    result["bc_facture_confidence"] = conf
                    result["used_fuzzy"] = True
                    result["link_warnings"].append(
                        f"BC-FACTURE fuzzy link: '{bc.ref_bc}' ≈ '{facture.ref_bc_linked}' (confidence={conf:.2f})"
                    )
                else:
                    result["link_warnings"].append(
                        f"BC ref '{bc.ref_bc}' does not match FACTURE's linked ref '{facture.ref_bc_linked}'"
                    )
        else:
            result["bc_facture_linked"] = True
            result["bc_facture_confidence"] = 0.70
            result["link_warnings"].append("FACTURE has no ref_bc_linked — link assumed by document position")

    return result


def match_line_item(
    bc_line: LineItemSchema,
    bl_line: LineItemSchema | None,
    facture_line: LineItemSchema | None,
    ctx: MatchContext,
) -> LineComparisonResult:
    """
    Compare one BC line against its BL and FACTURE counterparts.
    All comparisons are deterministic — no AI, no ML.
    """
    mismatch_fields: list[str] = []
    confidence = min(
        bc_line.extraction_confidence,
        bl_line.extraction_confidence if bl_line else 1.0,
        facture_line.extraction_confidence if facture_line else 1.0,
    )

    ref = bc_line.ref_produit or bc_line.designation or f"line_{bc_line.line_number}"

    # Quantity comparisons
    qty_bc = _decimal(bc_line.qty)
    qty_bl = _decimal(bl_line.qty) if bl_line else None
    qty_fac = _decimal(facture_line.qty) if facture_line else None

    if bl_line and not _within_tolerance(qty_bc, qty_bl, ctx.qty_tolerance):
        mismatch_fields.append("qty_bc_vs_bl")
    if facture_line and not _within_tolerance(qty_bc, qty_fac, ctx.qty_tolerance):
        mismatch_fields.append("qty_bc_vs_facture")

    # Price comparison (BC vs FACTURE only — BL has no price)
    prix_bc = _decimal(bc_line.prix_unitaire)
    prix_fac = _decimal(facture_line.prix_unitaire) if facture_line else None

    if facture_line and prix_bc and prix_fac:
        if not _within_tolerance(prix_bc, prix_fac, ctx.price_tolerance):
            mismatch_fields.append("prix_unitaire")

    # TVA comparison
    tva_bc = _decimal(bc_line.tva_rate)
    tva_fac = _decimal(facture_line.tva_rate) if facture_line else None

    if facture_line and tva_bc and tva_fac:
        if not _within_tolerance(tva_bc, tva_fac, ctx.tva_tolerance):
            mismatch_fields.append("tva_rate")

    # Determine verdict
    if confidence < 0.70:
        verdict = LineVerdict.LOW_CONFIDENCE
    elif not bl_line and not facture_line:
        verdict = LineVerdict.PARTIAL_DATA
    elif mismatch_fields:
        verdict = LineVerdict.MISMATCH
    else:
        verdict = LineVerdict.MATCH

    return LineComparisonResult(
        ref_produit=ref,
        designation=bc_line.designation,
        qty_bc=float(qty_bc) if qty_bc else None,
        qty_bl=float(qty_bl) if qty_bl else None,
        qty_facture=float(qty_fac) if qty_fac else None,
        prix_bc=float(prix_bc) if prix_bc else None,
        prix_facture=float(prix_fac) if prix_fac else None,
        tva_bc=float(tva_bc) if tva_bc else None,
        tva_facture=float(tva_fac) if tva_fac else None,
        verdict=verdict,
        mismatch_fields=mismatch_fields,
        confidence=confidence,
    )


def run_three_way_match(
    bc: BonDeCommandeSchema,
    bl: BonDeLivraison | None,
    facture: FactureSchema | None,
    job_id: str,
    supplier_price_tolerance: float | None = None,
    supplier_qty_tolerance: float | None = None,
) -> MatchResultSchema:
    """
    Main entry point for 3-way matching.
    Accepts BC (required), BL and FACTURE (optional — handles partial documents).
    Returns a fully structured MatchResultSchema.
    """
    ctx = MatchContext(job_id=job_id)
    if supplier_price_tolerance is not None:
        ctx.price_tolerance = Decimal(str(supplier_price_tolerance))
    if supplier_qty_tolerance is not None:
        ctx.qty_tolerance = Decimal(str(supplier_qty_tolerance))

    # Step 1: Verify document links
    links = link_documents(bc, bl, facture, ctx)
    line_results: list[LineComparisonResult] = []

    # Step 2: Build lookup maps for BL and FACTURE lines by normalized ref_produit
    bl_line_map: dict[str, LineItemSchema] = {}
    if bl:
        for line in bl.lines:
            if line.ref_produit_normalized:
                bl_line_map[line.ref_produit_normalized] = line

    facture_line_map: dict[str, LineItemSchema] = {}
    if facture:
        for line in facture.lines:
            if line.ref_produit_normalized:
                facture_line_map[line.ref_produit_normalized] = line

    matched_bl_refs: set[str] = set()
    matched_fac_refs: set[str] = set()

    # Step 3: For each BC line, find corresponding BL and FACTURE lines
    for bc_line in bc.lines:
        bc_ref = bc_line.ref_produit_normalized or ""

        bl_line = None
        fac_line = None

        # Try exact match first, then fuzzy
        if bc_ref in bl_line_map:
            bl_line = bl_line_map[bc_ref]
            matched_bl_refs.add(bc_ref)
        else:
            # Fuzzy search across all BL refs
            for bl_ref, candidate in bl_line_map.items():
                matched, _ = product_refs_match(bc_ref, bl_ref)
                if matched and bl_ref not in matched_bl_refs:
                    bl_line = candidate
                    matched_bl_refs.add(bl_ref)
                    break

        if bc_ref in facture_line_map:
            fac_line = facture_line_map[bc_ref]
            matched_fac_refs.add(bc_ref)
        else:
            for fac_ref, candidate in facture_line_map.items():
                matched, _ = product_refs_match(bc_ref, fac_ref)
                if matched and fac_ref not in matched_fac_refs:
                    fac_line = candidate
                    matched_fac_refs.add(fac_ref)
                    break

        # If BC line not found in either BL or FACTURE
        if bl and not bl_line:
            line_results.append(LineComparisonResult(
                ref_produit=bc_ref or f"line_{bc_line.line_number}",
                designation=bc_line.designation,
                qty_bc=float(bc_line.qty) if bc_line.qty else None,
                prix_bc=float(bc_line.prix_unitaire) if bc_line.prix_unitaire else None,
                verdict=LineVerdict.MISSING,
                mismatch_fields=["ref_produit"],
                confidence=1.0,
                notes="Product in BC not found in BL",
            ))
            continue

        result = match_line_item(bc_line, bl_line, fac_line, ctx)
        line_results.append(result)

    # Step 4: Check for EXTRA lines in BL/FACTURE not present in BC
    all_bc_refs = {
        line.ref_produit_normalized for line in bc.lines if line.ref_produit_normalized
    }

    if bl:
        for bl_ref, bl_line in bl_line_map.items():
            if bl_ref not in matched_bl_refs:
                is_in_bc = any(
                    product_refs_match(bl_ref, bc_ref)[0] for bc_ref in all_bc_refs
                )
                if not is_in_bc:
                    line_results.append(LineComparisonResult(
                        ref_produit=bl_ref,
                        designation=bl_line.designation,
                        qty_bl=float(bl_line.qty) if bl_line.qty else None,
                        verdict=LineVerdict.EXTRA,
                        mismatch_fields=["ref_produit"],
                        confidence=1.0,
                        notes="Product in BL not found in BC",
                    ))

    if facture:
        for fac_ref, fac_line in facture_line_map.items():
            if fac_ref not in matched_fac_refs:
                is_in_bc = any(
                    product_refs_match(fac_ref, bc_ref)[0] for bc_ref in all_bc_refs
                )
                if not is_in_bc:
                    line_results.append(LineComparisonResult(
                        ref_produit=fac_ref,
                        designation=fac_line.designation,
                        qty_facture=float(fac_line.qty) if fac_line.qty else None,
                        prix_facture=float(fac_line.prix_unitaire) if fac_line.prix_unitaire else None,
                        verdict=LineVerdict.EXTRA,
                        mismatch_fields=["ref_produit"],
                        confidence=1.0,
                        notes="Product in FACTURE not found in BC",
                    ))

    # Step 5: Compute counts and global verdict
    counts = {
        LineVerdict.MATCH: 0,
        LineVerdict.MISMATCH: 0,
        LineVerdict.MISSING: 0,
        LineVerdict.EXTRA: 0,
        LineVerdict.LOW_CONFIDENCE: 0,
        LineVerdict.PARTIAL_DATA: 0,
    }
    for r in line_results:
        counts[r.verdict] = counts.get(r.verdict, 0) + 1

    global_verdict = _compute_global_verdict(
        counts=counts,
        has_bl=bl is not None,
        has_facture=facture is not None,
        link_warnings=links["link_warnings"],
    )

    logger.info(
        "matching_complete",
        job_id=job_id,
        global_verdict=global_verdict,
        total_lines=len(line_results),
        **{k.value: v for k, v in counts.items()},
    )

    return MatchResultSchema(
        job_id=job_id,
        global_verdict=global_verdict,
        line_results=line_results,
        total_lines=len(line_results),
        match_count=counts[LineVerdict.MATCH],
        mismatch_count=counts[LineVerdict.MISMATCH],
        missing_count=counts[LineVerdict.MISSING],
        extra_count=counts[LineVerdict.EXTRA],
        low_confidence_count=counts[LineVerdict.LOW_CONFIDENCE] + counts[LineVerdict.PARTIAL_DATA],
        used_fuzzy_link=links["used_fuzzy"],
        bc_to_bl_link_confidence=links["bc_bl_confidence"],
        bc_to_facture_link_confidence=links["bc_facture_confidence"],
    )


def _compute_global_verdict(
    counts: dict,
    has_bl: bool,
    has_facture: bool,
    link_warnings: list[str],
) -> GlobalVerdict:
    """Deterministic global verdict from line-level counts."""

    # INCOMPLETE if a document type is entirely absent
    if not has_facture:
        return GlobalVerdict.INCOMPLETE

    # REJECTED if any price or reference mismatches
    if counts.get(LineVerdict.MISMATCH, 0) > 0:
        return GlobalVerdict.REJECTED

    # REVIEW if any low confidence or extra lines
    if counts.get(LineVerdict.LOW_CONFIDENCE, 0) > 0:
        return GlobalVerdict.REVIEW

    # PARTIAL if missing lines (product in BC not delivered/invoiced)
    if counts.get(LineVerdict.MISSING, 0) > 0:
        return GlobalVerdict.PARTIAL

    # REVIEW if extra lines detected
    if counts.get(LineVerdict.EXTRA, 0) > 0:
        return GlobalVerdict.REVIEW

    # REVIEW if fuzzy document links were used
    if link_warnings:
        return GlobalVerdict.REVIEW

    return GlobalVerdict.VALIDATED