import cv2
import numpy as np
from PIL import Image
import io
from app.core.logging import get_logger

logger = get_logger(__name__)


def preprocess_page_image(image_bytes: bytes) -> bytes:
    """
    Full preprocessing pipeline for scanned document pages.
    Returns cleaned PNG bytes ready for OCR.
    Steps: orientation fix → deskew → denoise → binarize → border removal
    """
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if img is None:
        raise ValueError("Failed to decode image bytes")
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = _deskew(gray)
    denoised = cv2.fastNlMeansDenoising(gray, h=10, templateWindowSize=7, searchWindowSize=21)
    _, binary = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    binary = _remove_borders(binary)
    success, encoded = cv2.imencode(".png", binary)
    if not success:
        raise ValueError("Failed to encode preprocessed image")
    return encoded.tobytes()


def _deskew(gray: np.ndarray) -> np.ndarray:
    """
    Detect and correct document skew using Hough line detection.
    Corrects angles up to ±15 degrees.
    """
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)
    lines = cv2.HoughLines(edges, 1, np.pi / 180, threshold=100)

    if lines is None:
        return gray
    angles = []
    for line in lines[:20]: 
        rho, theta = line[0]
        angle = (theta * 180 / np.pi) - 90
        if -15 < angle < 15:
            angles.append(angle)

    if not angles:
        return gray

    median_angle = np.median(angles)

    if abs(median_angle) < 0.5: 
        return gray
    h, w = gray.shape
    center = (w // 2, h // 2)
    rotation_matrix = cv2.getRotationMatrix2D(center, median_angle, 1.0)
    rotated = cv2.warpAffine(
        gray, rotation_matrix, (w, h),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE
    )

    logger.debug("deskew_applied", angle=float(median_angle))
    return rotated


def _remove_borders(binary: np.ndarray, border_size: int = 10) -> np.ndarray:
    """Remove scanner border artifacts by cropping a small margin."""
    h, w = binary.shape
    return binary[border_size:h-border_size, border_size:w-border_size]