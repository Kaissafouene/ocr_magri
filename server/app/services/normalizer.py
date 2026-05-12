import re
from datetime import date
from decimal import Decimal
from dateutil import parser as dateutil_parser
from app.utils.number_parser import parse_french_number
from app.core.logging import get_logger

logger = get_logger(__name__)
_OCR_CHAR_MAP = {
    "O": "0", 
    "o": "0",
    "l": "1",
    "I": "1",
    "S": "5",
    "B": "8",
    "G": "6",
    "Z": "2",
    " ": "",
}

def correct_ocr_numeric(raw: str) -> str:
    """
    Apply OCR character corrections ONLY to numeric and reference fields.
    Do NOT apply to description/designation fields.
    """
    if not raw:
        return raw
    result = []
    for char in raw:
        result.append(_OCR_CHAR_MAP.get(char, char))
    return "".join(result)


def normalize_reference(raw: str) -> str:
    """Normalize a document or product reference number."""
    if not raw:
        return ""
    corrected = correct_ocr_numeric(raw)
    return corrected.strip().upper()


def normalize_number(raw: str, supplier_locale: str = "fr") -> Decimal | None:
    """
    Parse and normalize a numeric value from OCR output.
    Applies OCR char correction first, then locale-aware number parsing.
    """
    if not raw:
        return None
    corrected = correct_ocr_numeric(str(raw))
    result = parse_french_number(corrected)
    if result is None:
        logger.debug("number_parse_failed", raw=raw, corrected=corrected)
    return result


def normalize_date(raw: str, supplier_date_fmt: str | None = None) -> date | None:
    """
    Parse a date string to a Python date object.
    Tries supplier-specific format first, then common French formats, then dateutil.
    Always stores internally as ISO 8601.
    """
    if not raw:
        return None

    raw = raw.strip()
    if supplier_date_fmt:
        try:
            from datetime import datetime
            return datetime.strptime(raw, supplier_date_fmt).date()
        except ValueError:
            pass
    french_formats = [
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%d.%m.%Y",
        "%Y-%m-%d",
        "%d/%m/%y",
        "%d %B %Y",  
    ]

    for fmt in french_formats:
        try:
            from datetime import datetime
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    # Fallback: dateutil parser (handles many edge cases)
    try:
        return dateutil_parser.parse(raw, dayfirst=True).date()
    except Exception:
        logger.debug("date_parse_failed", raw=raw)
        return None


def normalize_text(raw: str) -> str:
    """Clean a text field: strip whitespace, collapse multiple spaces."""
    if not raw:
        return ""
    return re.sub(r"\s+", " ", raw.strip())