import json
import re
from dataclasses import dataclass
from enum import Enum

import httpx

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class DocType(str, Enum):
    BC = "BC"
    BL = "BL"
    FACTURE = "FACTURE"
    UNKNOWN = "UNKNOWN"


@dataclass
class ClassificationResult:
    doc_type: DocType
    confidence: float
    source_tier: int  # 1=rule, 2=LLM, 3=human
    reasoning: str = ""


_BC_KEYWORDS = [
    r"\bBON\s+DE\s+COMMANDE\b",
    r"\bBON\s+COMMANDE\b",
    r"\bORDRE\s+D[''E]ACHAT\b",
    r"\bCOMMANDE\s+N[°o]\b",
    r"\bN[°o]\s*BC[-\s]\d",
    r"\bBC[-/]\d{4}",
    r"\bPURCHASE\s+ORDER\b",
    r"\bP\.?\s*O\.?\b",
]

_BL_KEYWORDS = [
    r"\bBON\s+DE\s+LIVRAISON\b",
    r"\bBON\s+LIVRAISON\b",
    r"\bLIVRAISON\s+N[°o]\b",
    r"\bN[°o]\s*BL[-\s]\d",
    r"\bBL[-/]\d{4}",
    r"\bDELIVERY\s+NOTE\b",
    r"\bBORDEREAU\s+DE\s+LIVRAISON\b",
]

_FACTURE_KEYWORDS = [
    r"\bFACTURE\b",
    r"\bFACTURE\s+N[°o]\b",
    r"\bN[°o]\s*FAC[-\s]\d",
    r"\bFAC[-/]\d{4}",
    r"\bINVOICE\b",
    r"\bAVOIR\b",
    r"\bFACT\s+N[°o]\b",
]


def classify_page_rule_based(text: str) -> ClassificationResult:
    """
    Tier 1: Rule-based page classification.
    Examines the top 40% of page text for document type keywords.
    Returns confidence 0.0-1.0.
    """
    if not text or len(text.strip()) < 10:
        return ClassificationResult(
            doc_type=DocType.UNKNOWN,
            confidence=0.0,
            source_tier=1,
            reasoning="Insufficient text for classification",
        )

    lines = text.splitlines()
    top_section = "\n".join(lines[: max(1, len(lines) * 4 // 10)]).upper()
    full_text_upper = text.upper()

    scores: dict[DocType, float] = {
        DocType.BC: 0.0,
        DocType.BL: 0.0,
        DocType.FACTURE: 0.0,
    }

    for pattern in _BC_KEYWORDS:
        if re.search(pattern, top_section):
            scores[DocType.BC] += 0.4
        elif re.search(pattern, full_text_upper):
            scores[DocType.BC] += 0.15

    for pattern in _BL_KEYWORDS:
        if re.search(pattern, top_section):
            scores[DocType.BL] += 0.4
        elif re.search(pattern, full_text_upper):
            scores[DocType.BL] += 0.15

    for pattern in _FACTURE_KEYWORDS:
        if re.search(pattern, top_section):
            scores[DocType.FACTURE] += 0.4
        elif re.search(pattern, full_text_upper):
            scores[DocType.FACTURE] += 0.15

    scores = {key: min(value, 1.0) for key, value in scores.items()}

    best_type = max(scores, key=lambda key: scores[key])
    best_score = scores[best_type]
    if best_score < 0.15:
        return ClassificationResult(
            doc_type=DocType.UNKNOWN,
            confidence=best_score,
            source_tier=1,
            reasoning=f"No clear keyword match. Scores: {scores}",
        )

    sorted_scores = sorted(scores.values(), reverse=True)
    if len(sorted_scores) > 1 and (sorted_scores[0] - sorted_scores[1]) < 0.1:
        best_score *= 0.7

    logger.debug("rule_classification", doc_type=best_type, confidence=best_score, scores=scores)

    return ClassificationResult(
        doc_type=best_type,
        confidence=min(best_score, 1.0),
        source_tier=1,
        reasoning=f"Keyword match. Scores: {scores}",
    )


async def classify_page_llm(text: str, image_b64: str | None = None) -> ClassificationResult:
    """
    Tier 2: LLM-based page classification.
    Called only when rule-based confidence < threshold.
    Returns structured JSON only. temperature=0.
    """
    system_prompt = """You are a document classification expert for a Tunisian manufacturing company.
You must classify a document page as one of: BC (Bon de Commande / Purchase Order), BL (Bon de Livraison / Delivery Note), FACTURE (Invoice), or UNKNOWN.

Respond ONLY with this exact JSON format, nothing else:
{
  "doc_type": "BC" | "BL" | "FACTURE" | "UNKNOWN",
  "confidence": 0.0 to 1.0,
  "reasoning": "brief explanation in one sentence"
}

Rules:
- BC = purchase order, lists products to be ordered with quantities and agreed prices
- BL = delivery note, confirms physical delivery of goods, usually no prices
- FACTURE = invoice, includes prices, totals, TVA, payment terms
- UNKNOWN = cannot determine with confidence"""

    user_content = f"Classify this document page:\n\n---\n{text[:3000]}\n---"

    payload = {
        "model": settings.llm_model,
        "max_tokens": 200,
        "temperature": settings.llm_temperature,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
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
        parsed = json.loads(raw_text)
        doc_type = DocType(parsed["doc_type"])
        confidence = float(parsed.get("confidence", 0.7))
        reasoning = parsed.get("reasoning", "")

        logger.info("llm_classification", doc_type=doc_type, confidence=confidence)

        return ClassificationResult(
            doc_type=doc_type,
            confidence=confidence,
            source_tier=2,
            reasoning=reasoning,
        )
    except (json.JSONDecodeError, KeyError, ValueError) as exc:
        logger.error("llm_classification_parse_error", error=str(exc))
        return ClassificationResult(
            doc_type=DocType.UNKNOWN,
            confidence=0.0,
            source_tier=2,
            reasoning=f"LLM response parse failed: {exc}",
        )
    except httpx.HTTPError as exc:
        logger.error("llm_classification_http_error", error=str(exc))
        return ClassificationResult(
            doc_type=DocType.UNKNOWN,
            confidence=0.0,
            source_tier=2,
            reasoning=f"LLM API call failed: {exc}",
        )


async def classify_page(
    text: str,
    image_b64: str | None = None,
) -> ClassificationResult:
    """
    Full classification cascade:
    Tier 1 (rules) -> Tier 2 (LLM if needed) -> UNKNOWN if both fail.
    """
    result = classify_page_rule_based(text)
    if result.confidence >= settings.classification_confidence_threshold:
        return result

    logger.info(
        "rule_classification_insufficient",
        confidence=result.confidence,
        falling_back_to="LLM",
    )

    if settings.openai_api_key:
        llm_result = await classify_page_llm(text, image_b64)
        if llm_result.confidence >= 0.70:
            return llm_result

    return ClassificationResult(
        doc_type=DocType.UNKNOWN,
        confidence=0.0,
        source_tier=3,
        reasoning="Both rule-based and LLM classification failed. Requires human review.",
    )
