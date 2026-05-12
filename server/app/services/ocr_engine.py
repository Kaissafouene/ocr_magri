import pytesseract
from pytesseract import Output
import numpy as np
import cv2
from dataclasses import dataclass, field
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class OCRResult:
    full_text: str
    word_confidences: list[int]      # 0-100 per word
    mean_confidence: float
    lines: list[str]                  # text split by line
    raw_data: dict = field(default_factory=dict)  # full pytesseract output


def run_tesseract(image_bytes: bytes) -> OCRResult:
    """
    Run Tesseract OCR on preprocessed image bytes.
    Returns structured result with per-word confidence scores.
    Language: French (fra) — handles accents, currency symbols, French number formats.
    """
    pytesseract.pytesseract.tesseract_cmd = settings.tesseract_cmd

    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_GRAYSCALE)

    if img is None:
        raise ValueError("Cannot decode image for OCR")
    config = f"--oem 3 --psm 6 -l {settings.tesseract_language}"
    data = pytesseract.image_to_data(
        img,
        config=config,
        output_type=Output.DICT
    )
    word_confidences = []
    words = []
    for i, word in enumerate(data["text"]):
        conf = int(data["conf"][i])
        if conf > 0 and word.strip():
            word_confidences.append(conf)
            words.append(word)

    mean_conf = (sum(word_confidences) / len(word_confidences) / 100.0) if word_confidences else 0.0
    full_text = pytesseract.image_to_string(img, config=config)
    lines = [ln.strip() for ln in full_text.splitlines() if ln.strip()]

    result = OCRResult(
        full_text=full_text,
        word_confidences=word_confidences,
        mean_confidence=mean_conf,
        lines=lines,
        raw_data=data,
    )

    logger.debug(
        "ocr_complete",
        mean_confidence=round(mean_conf, 3),
        word_count=len(word_confidences),
        line_count=len(lines),
    )

    return result


def get_field_confidence(ocr_data: dict, field_text: str) -> float:
    """
    Given OCR raw data and an extracted field value,
    estimate the confidence of that specific field by
    finding the words that compose it and averaging their confidence.
    """
    if not field_text or not ocr_data:
        return 0.5

    field_words = field_text.strip().upper().split()
    matched_confidences = []

    for i, word in enumerate(ocr_data.get("text", [])):
        if word.strip().upper() in field_words:
            conf = int(ocr_data["conf"][i])
            if conf > 0:
                matched_confidences.append(conf)

    if not matched_confidences:
        return 0.7

    return sum(matched_confidences) / len(matched_confidences) / 100.0