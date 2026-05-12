import fitz 
from dataclasses import dataclass
from enum import Enum


class PageSourceType(str, Enum):
    NATIVE = "NATIVE"
    SCANNED = "SCANNED"


@dataclass
class PageAnalysis:
    page_number: int         
    source_type: PageSourceType
    char_count: int
    image_coverage_ratio: float
    raw_text: str          
    width: float
    height: float


def analyze_pdf_pages(pdf_bytes: bytes) -> list[PageAnalysis]:
    """
    Open PDF in memory, analyze each page.
    Determines NATIVE vs SCANNED for each page individually.
    NATIVE  = has a text layer with meaningful content
    SCANNED = image-only, requires OCR
    """
    results: list[PageAnalysis] = []

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")

    for page_num in range(len(doc)):
        page = doc[page_num]
        rect = page.rect
        raw_text = page.get_text("text").strip()
        char_count = len(raw_text)
        image_list = page.get_images(full=True)
        image_coverage = 0.0
        if image_list:
            total_image_area = 0.0
            page_area = rect.width * rect.height
            for img in image_list:
                for item in page.get_image_rects(img[0]):
                    total_image_area += item.width * item.height
            if page_area > 0:
                image_coverage = min(total_image_area / page_area, 1.0)
        is_native = char_count > 50 and image_coverage < 0.3

        results.append(PageAnalysis(
            page_number=page_num,
            source_type=PageSourceType.NATIVE if is_native else PageSourceType.SCANNED,
            char_count=char_count,
            image_coverage_ratio=image_coverage,
            raw_text=raw_text if is_native else "",
            width=rect.width,
            height=rect.height,
        ))

    doc.close()
    return results


def extract_page_as_image(pdf_bytes: bytes, page_number: int, dpi: int = 300) -> bytes:
    """Render a specific page to PNG bytes at the given DPI."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    page = doc[page_number]
    matrix = fitz.Matrix(dpi / 72, dpi / 72)
    pix = page.get_pixmap(matrix=matrix, colorspace=fitz.csRGB)
    image_bytes = pix.tobytes("png")
    doc.close()
    return image_bytes


def get_page_count(pdf_bytes: bytes) -> int:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    count = len(doc)
    doc.close()
    return count