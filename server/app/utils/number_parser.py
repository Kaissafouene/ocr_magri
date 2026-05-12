import re
from decimal import Decimal, InvalidOperation


def parse_french_number(raw: str) -> Decimal | None:
    """
    Parse numbers in French locale format.
    Handles:
      "1 200,50"    → 1200.50   (space thousands sep, comma decimal)
      "1.200,50"    → 1200.50   (period thousands sep, comma decimal)
      "1,200.50"    → 1200.50   (comma thousands sep, period decimal)
      "1200.50"     → 1200.50   (plain international)
      "1 200"       → 1200      (whole number, space thousands)
      "1200"        → 1200
    """
    if not raw:
        return None

    raw = raw.strip()
    raw = re.sub(r"[€$£\s]", "", raw)
    raw = re.sub(r"[^\d.,]", "", raw)

    if not raw:
        return None
    comma_count = raw.count(",")
    dot_count = raw.count(".")

    try:
        if comma_count == 1 and dot_count == 0:
            parts = raw.split(",")
            if len(parts[1]) <= 2:
                raw = raw.replace(",", ".")
            else:
                raw = raw.replace(",", "")
        elif dot_count == 1 and comma_count == 0:
            parts = raw.split(".")
            if len(parts[1]) <= 2:
                pass 
            else:
                raw = raw.replace(".", "")
        elif comma_count == 1 and dot_count >= 1:
            raw = raw.replace(".", "").replace(",", ".")
        elif dot_count == 1 and comma_count >= 1:
            raw = raw.replace(",", "")
        else:
            raw = re.sub(r"[,.](?=.*[,.])", "", raw)
            raw = raw.replace(",", ".")

        return Decimal(raw)

    except InvalidOperation:
        return None