import cv2
import numpy as np
from PIL import Image


def preprocess(img: Image.Image) -> Image.Image:
    """
    Universal preprocessing engine for Indian IDs.
    Handles deskewing, background suppression, and contrast normalization.
    """
    img_cv = _pil_to_cv(img)
    
    # 1. High-Precision Threshold: Best for noisy screenshots and small text
    standard_width = 1600
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
    
    # 4. Sharpening & Denoising
    denoised = cv2.fastNlMeansDenoising(division, h=10)
    
    # Final normalization
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    final = clahe.apply(denoised)
    
    return _cv_to_pil(final)


def _pil_to_cv(img: Image.Image) -> np.ndarray:
    return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)


def _cv_to_pil(img: np.ndarray) -> Image.Image:
    if len(img.shape) == 2:
        return Image.fromarray(img)
    return Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))


def _deskew_image(img: np.ndarray, gray: np.ndarray) -> np.ndarray:
    thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
    coords = np.column_stack(np.where(thresh > 0))
    if len(coords) == 0: return img
    
    rect = cv2.minAreaRect(coords)
    angle = rect[-1]
    
    # Normalize angle
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle
        
    # Limit angle correction to avoid extreme flips
    if abs(angle) > 20: return img
    
    (h, w) = img.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    
    return rotated
