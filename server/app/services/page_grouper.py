import re
from dataclasses import dataclass, field
from app.services.classifier import DocType, ClassificationResult
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class PageClassified:
    page_number: int
    doc_type: DocType
    confidence: float
    source_tier: int
    raw_text: str
    ref_hint: str = "" 


@dataclass
class DocumentGroup:
    """A logical document assembled from one or more consecutive pages."""
    doc_type: DocType
    pages: list[int]          
    ref_document: str = ""
    classification_confidence: float = 1.0
    source_tier: int = 1
    combined_text: str = ""
_REF_PATTERNS = [
    r"(?:N[°o]?\s*)?BC[-\s/]?\d{2,4}[-\s/]?\d{2,6}",
    r"(?:N[°o]?\s*)?BL[-\s/]?\d{2,4}[-\s/]?\d{2,6}",
    r"(?:N[°o]?\s*)?FAC[-\s/]?\d{2,4}[-\s/]?\d{2,6}",
    r"(?:N[°o]?\s*)?FACT[-\s/]?\d{2,4}[-\s/]?\d{2,6}",
    r"\d{4}[-/]\d{3,6}",  # Generic number pattern
]

_CONTINUATION_PATTERNS = [
    r"PAGE\s+\d+\s+(?:OF|SUR|DE)\s+\d+",
    r"SUITE\b",
    r"SUITE\s+ET\s+FIN\b",
    r"\d+\s*/\s*\d+",   # "1/2" format
]


def extract_ref_hint(text: str) -> str:
    """Try to extract a document reference number from page text."""
    text_upper = text.upper()
    for pattern in _REF_PATTERNS:
        match = re.search(pattern, text_upper)
        if match:
            return match.group(0).strip().replace(" ", "").replace("\t", "")
    return ""


def is_continuation_page(text: str) -> bool:
    """Detect if this is a continuation page (page 2 of 2, SUITE, etc.)."""
    text_upper = text.upper()
    for pattern in _CONTINUATION_PATTERNS:
        if re.search(pattern, text_upper):
            return True
    return False


def group_pages_into_documents(classified_pages: list[PageClassified]) -> list[DocumentGroup]:
    """
    Assemble individually classified pages into logical document groups.

    Logic:
    1. Consecutive pages of same doc_type → same document IF refs match or continuation detected
    2. If ref_hint changes between same-type pages → different document (e.g., two BC in one PDF)
    3. UNKNOWN pages are isolated as their own group for human review
    """
    if not classified_pages:
        return []

    groups: list[DocumentGroup] = []
    current_group: DocumentGroup | None = None

    for page in classified_pages:
        if page.doc_type == DocType.UNKNOWN:
            if current_group:
                groups.append(current_group)
                current_group = None
            groups.append(DocumentGroup(
                doc_type=DocType.UNKNOWN,
                pages=[page.page_number],
                ref_document=page.ref_hint,
                classification_confidence=page.confidence,
                source_tier=page.source_tier,
                combined_text=page.raw_text,
            ))
            continue

        if current_group is None:
            current_group = DocumentGroup(
                doc_type=page.doc_type,
                pages=[page.page_number],
                ref_document=page.ref_hint,
                classification_confidence=page.confidence,
                source_tier=page.source_tier,
                combined_text=page.raw_text,
            )
            continue
        same_type = (page.doc_type == current_group.doc_type)
        continuation = is_continuation_page(page.raw_text)
        refs_match = (
            not page.ref_hint  
            or not current_group.ref_document
            or page.ref_hint == current_group.ref_document
        )

        if same_type and (continuation or refs_match):
            current_group.pages.append(page.page_number)
            current_group.combined_text += "\n" + page.raw_text
            current_group.classification_confidence = min(
                current_group.classification_confidence,
                page.confidence
            )
            if not current_group.ref_document and page.ref_hint:
                current_group.ref_document = page.ref_hint
        else:
            groups.append(current_group)
            current_group = DocumentGroup(
                doc_type=page.doc_type,
                pages=[page.page_number],
                ref_document=page.ref_hint,
                classification_confidence=page.confidence,
                source_tier=page.source_tier,
                combined_text=page.raw_text,
            )

    if current_group:
        groups.append(current_group)

    logger.info("pages_grouped", total_pages=len(classified_pages), groups_formed=len(groups))
    return groups