import cv2
import numpy as np
from PIL import Image


def preprocess(img: Image.Image) -> Image.Image:
    """
    Universal preprocessing engine for Indian IDs.
    Handles deskewing, background suppression, and contrast normalization.
    """
    img_cv = _pil_to_cv(img)
    
    # 1. Standardization: Upscale to a fixed width for consistent coordinate mapping
    standard_width = 3000
    h, w = img_cv.shape[:2]
    scale = standard_width / w
    img_cv = cv2.resize(img_cv, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    
    # 2. Alignment: Correct rotation (Deskew)
    gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
    img_cv = _deskew_image(img_cv, gray)
    gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY) # update gray after deskew
    
    # 3. Dynamic Background Suppression
    # This removes the dominant card color (blue for e-PAN, etc.)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (21, 21))
    bg = cv2.morphologyEx(gray, cv2.MORPH_DILATE, kernel)
    division = cv2.divide(gray, bg, scale=255)
    
    # 4. Contrast Stretch & Sharpen
    normalized = cv2.normalize(division, None, 0, 255, cv2.NORM_MINMAX)
    kernel_sharpen = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
    sharpened = cv2.filter2D(normalized, -1, kernel_sharpen)
    
    return Image.fromarray(sharpened)


def _pil_to_cv(img: Image.Image) -> np.ndarray:
    return cv2.cvtColor(np.array(img.convert("RGB")), cv2.COLOR_RGB2BGR)


def _deskew_image(img: np.ndarray, gray: np.ndarray) -> np.ndarray:
    """Detects text orientation and rotates the image to be horizontal."""
    # Find all text-like contours
    thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
    coords = np.column_stack(np.where(thresh > 0))
    angle = cv2.minAreaRect(coords)[-1]
    
    # Normalize angle
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle
        
    if abs(angle) < 0.5:
        return img
        
    (h, w) = img.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    return rotated
