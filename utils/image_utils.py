import cv2
import numpy as np
from PIL import Image


def preprocess(img: Image.Image) -> Image.Image:
    """
    High-fidelity grayscale preprocessing for Tesseract LSTM.
    """
    img_cv = _pil_to_cv(img)
    gray = _to_grayscale(img_cv)
    
    # 1. Upscale significantly (Tesseract loves large letters)
    gray = _upscale_if_needed(gray, min_width=3000)
    
    # 2. Subtle Denoise to remove WhatsApp JPEG artifacts
    denoised = cv2.fastNlMeansDenoising(gray, h=10)
    
    # 3. Contrast Normalization
    normalized = cv2.normalize(denoised, None, 0, 255, cv2.NORM_MINMAX)
    
    return Image.fromarray(normalized)


# ── helpers ──────────────────────────────────────────────────────────────────

def _pil_to_cv(img: Image.Image) -> np.ndarray:
    return cv2.cvtColor(np.array(img.convert("RGB")), cv2.COLOR_RGB2BGR)


def _to_grayscale(img_cv: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)


def _upscale_if_needed(gray: np.ndarray, min_width: int = 1200) -> np.ndarray:
    h, w = gray.shape
    if w < min_width:
        scale = min_width / w
        gray = cv2.resize(gray, None, fx=scale, fy=scale,
                          interpolation=cv2.INTER_CUBIC)
    return gray


def _denoise(gray: np.ndarray) -> np.ndarray:
    return cv2.fastNlMeansDenoising(gray, h=10, templateWindowSize=7,
                                    searchWindowSize=21)


def _binarize(gray: np.ndarray) -> np.ndarray:
    return cv2.adaptiveThreshold(
        gray, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        blockSize=11, C=2
    )


def _deskew(binary: np.ndarray) -> np.ndarray:
    """Correct slight rotation using minimum-area rectangle on text blobs."""
    coords = np.column_stack(np.where(binary < 128))
    if coords.size == 0:
        return binary

    angle = cv2.minAreaRect(coords)[-1]
    # minAreaRect returns angles in [-90, 0); map to [-45, 45)
    if angle < -45:
        angle = 90 + angle

    if abs(angle) < 0.5:  # not worth rotating
        return binary

    (h, w) = binary.shape
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(binary, M, (w, h),
                             flags=cv2.INTER_CUBIC,
                             borderMode=cv2.BORDER_REPLICATE)
    return rotated
