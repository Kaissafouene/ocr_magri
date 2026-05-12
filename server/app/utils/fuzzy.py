from Levenshtein import distance as levenshtein_distance


def normalize_ref(ref: str) -> str:
    """Normalize a document reference for comparison."""
    if not ref:
        return ""
    return ref.strip().upper().replace(" ", "").replace("\t", "").replace("-", "").replace("/", "")


def refs_match_exact(ref_a: str, ref_b: str) -> bool:
    return normalize_ref(ref_a) == normalize_ref(ref_b)


def refs_match_fuzzy(ref_a: str, ref_b: str, max_distance: int = 2) -> tuple[bool, float]:
    """
    Returns (is_match, confidence).
    Confidence = 1.0 for exact match, decreasing for fuzzy.
    """
    norm_a = normalize_ref(ref_a)
    norm_b = normalize_ref(ref_b)

    if not norm_a or not norm_b:
        return False, 0.0

    if norm_a == norm_b:
        return True, 1.0

    dist = levenshtein_distance(norm_a, norm_b)
    max_len = max(len(norm_a), len(norm_b))

    if dist <= max_distance and max_len > 0:
        confidence = 1.0 - (dist / max_len)
        return True, confidence

    return False, 0.0


def product_refs_match(ref_a: str, ref_b: str, max_distance: int = 1) -> tuple[bool, float]:
    """
    Product reference matching is stricter than document reference matching.
    Default max_distance=1 (one OCR character error allowed).
    """
    return refs_match_fuzzy(ref_a, ref_b, max_distance)