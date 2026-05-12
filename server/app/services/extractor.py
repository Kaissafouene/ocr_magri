import re
import json
import httpx
from decimal import Decimal
from app.schemas.documents import (
    BonDeCommandeSchema, BonDeLivraison, FactureSchema,
    LineItemSchema, DocumentType, ExtractionTier
)
from app.services.page_grouper import DocumentGroup
from app.services.normalizer import (
    normalize_reference, normalize_number, normalize_date, normalize_text
)
from app.services.supplier_service import SupplierProfile, get_supplier_from_text
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# TIER 1: Template-Based Extraction
# ─────────────────────────────────────────────────────────────────────────────

# Regex
_HEADER_PATTERNS = {
    "ref_bc": [
        r"(?:N[°o]?\s*(?:BC|BON\s*DE\s*COMMANDE))\s*[:\-]?\s*([A-Z0-9\-/]{3,30})",
        r"(?:COMMANDE\s*N[°o]?)\s*[:\-]?\s*([A-Z0-9\-/]{3,30})",
        r"(BC[-/]\d{2,4}[-/]\d{2,8})",
    ],
    "ref_bl": [
        r"(?:N[°o]?\s*(?:BL|BON\s*DE\s*LIVRAISON))\s*[:\-]?\s*([A-Z0-9\-/]{3,30})",
        r"(?:LIVRAISON\s*N[°o]?)\s*[:\-]?\s*([A-Z0-9\-/]{3,30})",
        r"(BL[-/]\d{2,4}[-/]\d{2,8})",
    ],
    "ref_facture": [
        r"(?:N[°o]?\s*(?:FAC(?:TURE)?|FACTURE))\s*[:\-]?\s*([A-Z0-9\-/]{3,30})",
        r"(?:FACTURE\s*N[°o]?)\s*[:\-]?\s*([A-Z0-9\-/]{3,30})",
        r"(FAC[-/]\d{2,4}[-/]\d{2,8})",
    ],
    "ref_bc_linked": [
        r"(?:BC|BON\s*DE\s*COMMANDE|REF\s*BC)\s*[:\-]?\s*([A-Z0-9\-/]{3,30})",
        r"(BC[-/]\d{2,4}[-/]\d{2,8})",
    ],
    "date": [
        r"(?:DATE|LE|DU)\s*[:\-]?\s*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})",
        r"(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})",
    ],
    "total_ht": [
        r"(?:TOTAL\s*H\.?\s*T\.?|MONTANT\s*HT|TOTAL\s*HORS\s*TAXES)\s*[:\-]?\s*([\d\s.,]+)",
    ],
    "total_ttc": [
        r"(?:TOTAL\s*T\.?\s*T\.?\s*C\.?|MONTANT\s*TTC|NET\s*À\s*PAYER)\s*[:\-]?\s*([\d\s.,]+)",
    ],
    "tva_rate": [
        r"(?:TVA|T\.V\.A\.)\s*(?:@|À|A|:)?\s*(\d{1,2}(?:[.,]\d{1,2})?)\s*%",
        r"(\d{1,2}(?:[.,]\d{1,2})?)\s*%\s*(?:TVA|T\.V\.A\.)",
    ],
    "supplier_name": [
        r"(?:FOURNISSEUR|VENDEUR|DE\s*:?)\s*[:\-]?\s*([A-ZÀ-Ÿa-zà-ÿ\s&\.]{3,80})",
    ],
}

# Table column header patterns
_TABLE_HEADER_PATTERNS = {
    "ref_produit": [r"R[ÉE]F[.\s]*(?:PRODUIT|ART|ARTICLE)?", r"CODE\s*(?:ARTICLE|PRODUIT)?", r"R[ÉE]F\.?"],
    "designation": [r"D[ÉE]SIGNATION", r"LIBELL[ÉE]", r"DESCRIPTION", r"ARTICLE"],
    "qty": [r"(?:QT[ÉE]|QUANTIT[ÉE]|QTE|NB)\b", r"QT[ÉE]\.?"],
    "unit": [r"UNIT[ÉE]", r"U\.?M\.?", r"MESURE"],
    "prix_unitaire": [r"PRIX\s*U(?:NIT\.?)?(?:\s*H\.?T\.?)?", r"P\.?\s*U\.?\s*H\.?T\.?", r"P\.?U\.?"],
    "tva_rate": [r"T\.?V\.?A\.?", r"TVA\s*%"],
    "total_ligne": [r"TOTAL\s*H\.?T\.?", r"MONTANT\s*H\.?T\.?", r"TOTAL\s*LIGNE"],
}


def _extract_with_patterns(text: str, patterns: list[str], supplier_aliases: dict = None) -> tuple[str | None, float]:
    """Try each regex pattern in order, return first match + confidence."""
    text_upper = text.upper()
    if supplier_aliases:
        for alias, target_field in supplier_aliases.items():
            pass

    for pattern in patterns:
        match = re.search(pattern, text_upper, re.MULTILINE)
        if match:
            groups = match.groups()
            if groups:
                raw_value = groups[-1].strip()
                if raw_value:
                    return raw_value, 0.85
    return None, 0.0


def _extract_line_items(text: str, supplier_profile: "SupplierProfile | None" = None) -> list[LineItemSchema]:
    """
    Extract line items table from document text.
    Strategy: find table header row, then parse each subsequent row.
    """
    lines = text.splitlines()
    items: list[LineItemSchema] = []
    header_row_idx = -1
    col_positions: dict[str, int] = {}
    for i, line in enumerate(lines):
        line_upper = line.upper()
        found_cols = 0
        for col_name, patterns in _TABLE_HEADER_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, line_upper):
                    match = re.search(pattern, line_upper)
                    if match:
                        col_positions[col_name] = match.start()
                        found_cols += 1
                    break
        if found_cols >= 3:
            header_row_idx = i
            break

    if header_row_idx == -1:
        logger.debug("table_header_not_found", text_length=len(text))
        return items
    line_num = 0
    for line in lines[header_row_idx + 1:]:
        line = line.strip()
        if not line or len(line) < 5:
            continue
        if not re.search(r"\d", line):
            continue
        line_upper = line.upper()
        if any(kw in line_upper for kw in ["TOTAL HT", "SOUS-TOTAL", "TOTAL TTC", "NET À PAYER", "TVA"]):
            break
        parts = re.split(r"\s{2,}|\t", line) 
        parts = [p.strip() for p in parts if p.strip()]
        if len(parts) < 2:
            continue
        line_num += 1
        item = _parse_line_parts(parts, col_positions, line_num)
        if item:
            items.append(item)

    return items


def _parse_line_parts(parts: list[str], col_positions: dict, line_num: int) -> LineItemSchema | None:
    """Parse a split line into a LineItemSchema. Handles variable column counts."""
    if not parts:
        return None
    ref_produit = None
    designation = None
    qty = None
    prix_unitaire = None
    tva_rate = None
    total_ligne = None
    numeric_parts = []
    text_parts = []

    for part in parts:
        cleaned = re.sub(r"[€%\s]", "", part.replace(",", "."))
        try:
            float(cleaned)
            numeric_parts.append(part)
        except ValueError:
            text_parts.append(part)

    if text_parts:
        ref_produit = text_parts[0]
        designation = " ".join(text_parts[1:]) if len(text_parts) > 1 else None
    for part in numeric_parts:
        val = normalize_number(part)
        if val is None:
            continue
        if tva_rate is None and 0 < float(val) <= 30:
            if "%" in part:
                tva_rate = val
                continue
        if qty is None and val is not None and float(val) < 10000:
            qty = val
        elif prix_unitaire is None and val is not None:
            prix_unitaire = val
        elif total_ligne is None:
            total_ligne = val
    if not any([ref_produit, qty, prix_unitaire]):
        return None
    confidence = 0.75 if (ref_produit and qty) else 0.5
    return LineItemSchema(
        line_number=line_num,
        ref_produit=normalize_reference(ref_produit) if ref_produit else None,
        ref_produit_normalized=normalize_reference(ref_produit) if ref_produit else None,
        designation=normalize_text(designation) if designation else None,
        qty=qty,
        prix_unitaire=prix_unitaire,
        tva_rate=tva_rate,
        total_ligne_ht=total_ligne,
        extraction_confidence=confidence,
    )


def extract_document_template(
    group: DocumentGroup,
    supplier_profile: "SupplierProfile | None" = None,
) -> BonDeCommandeSchema | BonDeLivraison | FactureSchema | None:
    """
    Tier 1 extraction: template-based using regex patterns + supplier profile aliases.
    Returns the appropriate schema or None if extraction confidence is too low.
    """
    text = group.combined_text
    doc_type = group.doc_type
    field_confidence: dict[str, float] = {}
    if supplier_profile and supplier_profile.field_aliases:
        aliases = supplier_profile.field_aliases.get(doc_type.value, {})
        for alias, canonical in aliases.items():
            text = re.sub(re.escape(alias.upper()), canonical.upper(), text.upper(), flags=re.IGNORECASE)

    if doc_type == DocumentType.BC:
        ref_raw, ref_conf = _extract_with_patterns(text, _HEADER_PATTERNS["ref_bc"])
        date_raw, date_conf = _extract_with_patterns(text, _HEADER_PATTERNS["date"])
        supplier_raw, _ = _extract_with_patterns(text, _HEADER_PATTERNS["supplier_name"])
        if not ref_raw:
            return None 
        lines = _extract_line_items(text, supplier_profile)
        date_parsed = normalize_date(date_raw, supplier_profile.date_format if supplier_profile else None)
        field_confidence["ref_bc"] = ref_conf
        field_confidence["document_date"] = date_conf
        has_low_conf = any(v < 0.70 for v in field_confidence.values())
        return BonDeCommandeSchema(
            ref_bc=normalize_reference(ref_raw),
            document_date=date_parsed,
            supplier_name=normalize_text(supplier_raw) if supplier_raw else None,
            lines=lines,
            extraction_source_tier=ExtractionTier.TEMPLATE,
            extraction_confidence=min(field_confidence.values()) if field_confidence else 0.7,
            field_confidence_map=field_confidence,
            has_low_confidence_fields=has_low_conf,
        )

    elif doc_type == DocumentType.BL:
        ref_raw, ref_conf = _extract_with_patterns(text, _HEADER_PATTERNS["ref_bl"])
        ref_bc_raw, ref_bc_conf = _extract_with_patterns(text, _HEADER_PATTERNS["ref_bc_linked"])
        date_raw, date_conf = _extract_with_patterns(text, _HEADER_PATTERNS["date"])

        if not ref_raw:
            return None
        lines = _extract_line_items(text, supplier_profile)
        date_parsed = normalize_date(date_raw, supplier_profile.date_format if supplier_profile else None)
        field_confidence = {"ref_bl": ref_conf, "document_date": date_conf}
        return BonDeLivraison(
            ref_bl=normalize_reference(ref_raw),
            ref_bc_linked=normalize_reference(ref_bc_raw) if ref_bc_raw else None,
            document_date=date_parsed,
            lines=lines,
            extraction_source_tier=ExtractionTier.TEMPLATE,
            extraction_confidence=min(field_confidence.values()),
            field_confidence_map=field_confidence,
            has_low_confidence_fields=any(v < 0.70 for v in field_confidence.values()),
        )

    elif doc_type == DocumentType.FACTURE:
        ref_raw, ref_conf = _extract_with_patterns(text, _HEADER_PATTERNS["ref_facture"])
        ref_bc_raw, _ = _extract_with_patterns(text, _HEADER_PATTERNS["ref_bc_linked"])
        date_raw, date_conf = _extract_with_patterns(text, _HEADER_PATTERNS["date"])
        total_ht_raw, ht_conf = _extract_with_patterns(text, _HEADER_PATTERNS["total_ht"])
        total_ttc_raw, ttc_conf = _extract_with_patterns(text, _HEADER_PATTERNS["total_ttc"])
        tva_raw, tva_conf = _extract_with_patterns(text, _HEADER_PATTERNS["tva_rate"])

        if not ref_raw:
            return None
        lines = _extract_line_items(text, supplier_profile)
        date_parsed = normalize_date(date_raw, supplier_profile.date_format if supplier_profile else None)
        field_confidence = {
            "ref_facture": ref_conf,
            "document_date": date_conf,
            "total_ht": ht_conf,
            "total_ttc": ttc_conf,
        }

        return FactureSchema(
            ref_facture=normalize_reference(ref_raw),
            ref_bc_linked=normalize_reference(ref_bc_raw) if ref_bc_raw else None,
            document_date=date_parsed,
            total_ht=normalize_number(total_ht_raw) if total_ht_raw else None,
            total_ttc=normalize_number(total_ttc_raw) if total_ttc_raw else None,
            tva_rate=normalize_number(tva_raw) if tva_raw else None,
            lines=lines,
            extraction_source_tier=ExtractionTier.TEMPLATE,
            extraction_confidence=min(field_confidence.values()),
            field_confidence_map=field_confidence,
            has_low_confidence_fields=any(v < 0.70 for v in field_confidence.values()),
        )

    return None


# ─────────────────────────────────────────────────────────────────────────────
# TIER 3: LLM Fallback Extraction
# ─────────────────────────────────────────────────────────────────────────────

_LLM_SCHEMA_BY_TYPE = {
    DocumentType.BC: {
        "ref_bc": "string (document reference number)",
        "document_date": "string (DD/MM/YYYY)",
        "supplier_name": "string",
        "lines": [{
            "line_number": "integer",
            "ref_produit": "string",
            "designation": "string",
            "qty": "number",
            "unit": "string",
            "prix_unitaire": "number",
            "tva_rate": "number (percentage, e.g. 19)",
            "total_ligne_ht": "number"
        }]
    },
    DocumentType.BL: {
        "ref_bl": "string",
        "ref_bc_linked": "string or null",
        "document_date": "string (DD/MM/YYYY)",
        "supplier_name": "string",
        "lines": [{
            "line_number": "integer",
            "ref_produit": "string",
            "designation": "string",
            "qty": "number",
            "unit": "string"
        }]
    },
    DocumentType.FACTURE: {
        "ref_facture": "string",
        "ref_bc_linked": "string or null",
        "document_date": "string (DD/MM/YYYY)",
        "supplier_name": "string",
        "total_ht": "number",
        "total_tva": "number",
        "total_ttc": "number",
        "tva_rate": "number (percentage)",
        "lines": [{
            "line_number": "integer",
            "ref_produit": "string",
            "designation": "string",
            "qty": "number",
            "unit": "string",
            "prix_unitaire": "number",
            "tva_rate": "number",
            "total_ligne_ht": "number"
        }]
    },
}


async def extract_document_llm(
    group: DocumentGroup,
    validation_error: str | None = None,
) -> dict | None:
    """
    Tier 3 LLM extraction fallback.
    Sends document text to OpenAI with strict JSON instructions.
    Retries once on validation failure.
    Returns raw dict for caller to map to Pydantic schema.
    """
    schema = _LLM_SCHEMA_BY_TYPE.get(group.doc_type)
    if not schema:
        return None

    system_prompt = f"""You are a data extraction assistant for an accounting system.
Extract structured data from the document text below.

RULES — follow exactly:
1. Extract ONLY what is explicitly written in the document. Do NOT infer or calculate.
2. If a field is not visible or unclear, return null for that field.
3. Never guess quantities, prices, or reference numbers.
4. Return ONLY valid JSON matching the schema. No explanation, no markdown, no extra text.
5. For numbers: return plain decimals (e.g., 1200.50 not "1 200,50")
6. For dates: return as string in original format found in document

Required JSON schema:
{json.dumps(schema, indent=2)}"""

    error_note = ""
    if validation_error:
        error_note = f"\n\nNOTE: Your previous response failed validation with error: {validation_error}\nPlease fix and return correct JSON only."

    user_content = f"Document type: {group.doc_type.value}\n\nDocument text:\n---\n{group.combined_text[:4000]}\n---{error_note}"

    payload = {
        "model": settings.llm_model,
        "max_tokens": settings.llm_max_tokens,
        "temperature": settings.llm_temperature,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{settings.openai_base_url.rstrip('/')}/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.openai_api_key}",
                    "content-type": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()

        data = response.json()
        raw_text = data["choices"][0]["message"]["content"].strip()
        raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text, flags=re.MULTILINE)
        raw_text = re.sub(r"\s*```$", "", raw_text, flags=re.MULTILINE)
        return json.loads(raw_text)
    except (json.JSONDecodeError, KeyError) as e:
        logger.error("llm_extraction_parse_error", error=str(e), doc_type=group.doc_type)
        return None
    except httpx.HTTPError as e:
        logger.error("llm_extraction_http_error", error=str(e))
        return None


def map_llm_result_to_schema(
    raw: dict,
    doc_type: DocumentType,
) -> BonDeCommandeSchema | BonDeLivraison | FactureSchema | None:
    """Map LLM raw dict output to the appropriate Pydantic schema."""
    try:
        lines_raw = raw.get("lines", [])
        lines = []
        for i, ln in enumerate(lines_raw):
            lines.append(LineItemSchema(
                line_number=ln.get("line_number", i + 1),
                ref_produit=normalize_reference(ln.get("ref_produit", "")) or None,
                ref_produit_normalized=normalize_reference(ln.get("ref_produit", "")) or None,
                designation=normalize_text(ln.get("designation", "")),
                qty=normalize_number(str(ln["qty"])) if ln.get("qty") is not None else None,
                unit=ln.get("unit"),
                prix_unitaire=normalize_number(str(ln["prix_unitaire"])) if ln.get("prix_unitaire") is not None else None,
                tva_rate=normalize_number(str(ln["tva_rate"])) if ln.get("tva_rate") is not None else None,
                total_ligne_ht=normalize_number(str(ln["total_ligne_ht"])) if ln.get("total_ligne_ht") is not None else None,
                extraction_confidence=0.70,
            ))

        if doc_type == DocumentType.BC:
            return BonDeCommandeSchema(
                ref_bc=normalize_reference(raw["ref_bc"]),
                document_date=normalize_date(raw.get("document_date")),
                supplier_name=normalize_text(raw.get("supplier_name", "")),
                lines=lines,
                extraction_source_tier=ExtractionTier.LLM,
                extraction_confidence=0.70,
            )
        elif doc_type == DocumentType.BL:
            return BonDeLivraison(
                ref_bl=normalize_reference(raw["ref_bl"]),
                ref_bc_linked=normalize_reference(raw.get("ref_bc_linked") or ""),
                document_date=normalize_date(raw.get("document_date")),
                supplier_name=normalize_text(raw.get("supplier_name", "")),
                lines=lines,
                extraction_source_tier=ExtractionTier.LLM,
                extraction_confidence=0.70,
            )
        elif doc_type == DocumentType.FACTURE:
            return FactureSchema(
                ref_facture=normalize_reference(raw["ref_facture"]),
                ref_bc_linked=normalize_reference(raw.get("ref_bc_linked") or ""),
                document_date=normalize_date(raw.get("document_date")),
                supplier_name=normalize_text(raw.get("supplier_name", "")),
                total_ht=normalize_number(str(raw["total_ht"])) if raw.get("total_ht") else None,
                total_ttc=normalize_number(str(raw["total_ttc"])) if raw.get("total_ttc") else None,
                tva_rate=normalize_number(str(raw["tva_rate"])) if raw.get("tva_rate") else None,
                lines=lines,
                extraction_source_tier=ExtractionTier.LLM,
                extraction_confidence=0.70,
            )
    except (KeyError, TypeError, Exception) as e:
        logger.error("llm_schema_mapping_failed", error=str(e), doc_type=doc_type)
        return None
