import cv2
import numpy as np


def deskew(image: np.ndarray) -> np.ndarray:
    """
    Detects and corrects skew/tilt in a grayscale document image.
    Uses minAreaRect on non-zero pixels to calculate rotation angle.
    """
    inverted = cv2.bitwise_not(image)
    coords = np.column_stack(np.where(inverted > 0))

    if len(coords) == 0:
        return image

    angle = cv2.minAreaRect(coords)[-1]

    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle

    if abs(angle) < 0.5:
        return image

    (h, w) = image.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(
        image, M, (w, h),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE
    )
    return rotated


def preprocess_image(image_bytes: bytes) -> np.ndarray:
    """
    Optimized preprocessing pipeline:
    1. Grayscale conversion
    2. Fast denoising (median blur — much faster than NlMeans)
    3. Skew/tilt correction (deskew) — only if image is not too large
    4. Adaptive thresholding (shadows + uneven lighting)
    Returns a clean binary image ready for OCR/AI.

    Note: Upscaling removed — Tesseract handles native-res images well,
    and upscaling 2.5MB PDFs causes massive slowdowns.
    """
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if img is None:
        raise ValueError("Invalid image file or unable to decode. Please upload a valid JPG/PNG.")

    # Step 1: Grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Step 2: Fast denoising — median blur is ~50x faster than fastNlMeans
    # and sufficient for document cleanup
    denoised = cv2.medianBlur(gray, 3)

    # Step 3: Deskew (skip on very large images to stay fast)
    h, w = denoised.shape
    if h * w < 4_000_000:  # skip deskew for images > ~4MP
        denoised = deskew(denoised)

    # Step 4: Adaptive thresholding
    processed = cv2.adaptiveThreshold(
        denoised, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, 11, 2
    )

    return processed
