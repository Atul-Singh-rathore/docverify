import cv2
import numpy as np

def preprocess_image(image_bytes):
    """
    Reads uploaded image bytes, converts to grayscale, 
    removes noise, and prepares it for AI text extraction.
    """
    # Convert image bytes to numpy array
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if img is None:
        raise ValueError("Invalid image file or unable to decode.")

    # 1. Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # 2. Noise removal using Fast Nl Means Denoising
    denoised = cv2.fastNlMeansDenoising(gray, h=30)

    # 3. Adaptive Thresholding to handle shadows and uneven lighting
    processed = cv2.adaptiveThreshold(
        denoised, 255, 
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
        cv2.THRESH_BINARY, 11, 2
    )

    return processed