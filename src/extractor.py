import io
import re
import numpy as np
import pytesseract
from PIL import Image, ImageChops, ImageEnhance
import platform

# --- Tesseract path auto-configure for Windows ---
if platform.system() == "Windows":
    pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


# ─────────────────────────────────────────────────────────
# Field Extraction Regexes
# ─────────────────────────────────────────────────────────
# Fields that need strict case matching (no IGNORECASE)
STRICT_CASE_FIELDS = {"name"}

PATTERNS = {
    "name": [
        # Must have label prefix first
        r"(?:Name|Full Name|Issued to|Awarded to|This certifies that)\s*[:\-]?\s*([A-Z][a-z]+(?:\s[A-Z][a-z]+)+)",
        # Standalone Title Case full name on its own line (min 2 words, each 3+ chars)
        r"^([A-Z][a-z]{2,}(?:\s[A-Z][a-z]{2,})+)$",
    ],
    "dob": [
        r"(?:DOB|Date of Birth|D\.O\.B|Born)\s*[:\-]?\s*(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})",
        r"\b(\d{2}[\/\-]\d{2}[\/\-]\d{4})\b",
    ],
    "id_number": [
        r"(?:ID|ID No|Employee ID|Emp\. ID|ID Number|Reg\. No|Admission No)\s*[:\-]?\s*([A-Z0-9]{5,20})",
        r"\b([A-Z]{1,3}\d{5,10})\b",
        r"\b(\d{10,16})\b",
    ],
    "department": [
        r"(?:Dept|Department|DEPT|Division)\s*[:\-]?\s*([A-Za-z\s]+?)(?:\n|$)",
    ],
    "phone": [
        r"(?:\+91|0)?[\s\-]?([6-9]\d{9})",
    ],
    "email": [
        r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}",
    ],
}


def _match_patterns(text: str, patterns: list[str], strict_case: bool = False) -> str:
    flags = re.MULTILINE if strict_case else re.MULTILINE | re.IGNORECASE
    for pattern in patterns:
        match = re.search(pattern, text, flags)
        if match:
            return match.group(1).strip() if match.lastindex else match.group(0).strip()
    return "Not Found"


def extract_text_via_ocr(image: Image.Image) -> tuple[str, float]:
    """
    Single Tesseract call that returns BOTH raw text AND confidence score.
    Uses PSM 11 (sparse text) — works best for certificates, ID cards, complex layouts.
    Reconstructs text with proper line breaks so regex patterns work correctly.
    """
    try:
        # Convert to grayscale + mild sharpen — better for certificates than
        # aggressive contrast boost which can break stylized/serif characters
        from PIL import ImageFilter, ImageEnhance as IE
        gray = image.convert("L").convert("RGB")  # grayscale preserves structure
        enhanced = IE.Sharpness(gray).enhance(1.5)  # mild sharpen only

        # PSM 11 = sparse text (find as much text as possible, any order)
        # Better than PSM 6 for certificates, IDs, and non-uniform layouts
        config = r"--oem 3 --psm 11"
        data = pytesseract.image_to_data(enhanced, config=config, output_type=pytesseract.Output.DICT)

        # Reconstruct text preserving line structure (needed for regex multiline patterns)
        # Only keep words with confidence >= 30 AND length >= 2 to filter garbage fragments
        lines = {}
        for word, conf, line_num, block_num in zip(
            data["text"], data["conf"], data["line_num"], data["block_num"]
        ):
            w = word.strip()
            if not w or len(w) < 2:          # skip single-char garbage
                continue
            try:
                c = int(conf)
            except (ValueError, TypeError):
                continue
            if c < 30:                        # skip low-confidence fragments
                continue
            key = (block_num, line_num)
            lines.setdefault(key, []).append(w)

        raw_text = "\n".join(" ".join(words) for words in lines.values())

        # Confidence: average of all valid word confidences
        confs = []
        for conf in data["conf"]:
            try:
                c = int(conf)
                if c >= 0:
                    confs.append(c)
            except (ValueError, TypeError):
                continue
        avg_conf = round(sum(confs) / len(confs), 1) if confs else 0.0

        return raw_text.strip(), avg_conf
    except Exception as e:
        return f"[OCR Error: {e}]", 0.0


def parse_fields(text: str) -> dict:
    """
    Applies regex patterns to extract structured fields from raw OCR text.
    Uses strict case matching for name fields to avoid false positives.
    """
    fields = {}
    for field, patterns in PATTERNS.items():
        strict = field in STRICT_CASE_FIELDS
        fields[field] = _match_patterns(text, patterns, strict_case=strict)
    return fields


# ─────────────────────────────────────────────────────────
# Tamper Detection — ELA (Error Level Analysis)
# ─────────────────────────────────────────────────────────
def run_ela(image: Image.Image, quality: int = 90) -> dict:
    """
    Error Level Analysis — fast path optimized:
    - Resizes large images before ELA (biggest speed win)
    - Re-saves at known JPEG quality, computes pixel differences
    Returns tamper risk score 0–100 and a verdict.
    """
    try:
        img_rgb = image.convert("RGB")

        # ── Speed optimization: cap ELA image size at 1200px wide ──
        max_dim = 1200
        w, h = img_rgb.size
        if w > max_dim or h > max_dim:
            scale = max_dim / max(w, h)
            img_rgb = img_rgb.resize(
                (int(w * scale), int(h * scale)),
                Image.LANCZOS
            )

        buffer = io.BytesIO()
        img_rgb.save(buffer, format="JPEG", quality=quality)
        buffer.seek(0)
        recompressed = Image.open(buffer).convert("RGB")

        ela_image = ImageChops.difference(img_rgb, recompressed)

        extrema = ela_image.getextrema()
        max_diff = max([e[1] for e in extrema]) if extrema else 1
        if max_diff == 0:
            max_diff = 1

        scale_factor = 255.0 / max_diff
        ela_enhanced = ImageEnhance.Brightness(ela_image).enhance(scale_factor)

        ela_arr = np.array(ela_enhanced).astype(np.float32)
        flat = ela_arr.flatten()
        threshold = np.percentile(flat, 95)
        anomaly_pixels = flat[flat >= threshold]
        tamper_score = float(np.mean(anomaly_pixels)) / 255.0 * 100
        tamper_score = min(round(tamper_score, 1), 100.0)

        if tamper_score < 20:
            verdict = "✅ Authentic"
            risk = "Low"
        elif tamper_score < 50:
            verdict = "⚠️ Suspicious"
            risk = "Medium"
        else:
            verdict = "🚨 Likely Tampered"
            risk = "High"

        return {
            "ela_score": tamper_score,
            "risk_level": risk,
            "verdict": verdict,
            "details": f"ELA anomaly score: {tamper_score:.1f}/100"
        }

    except Exception as e:
        return {
            "ela_score": 0,
            "risk_level": "Unknown",
            "verdict": "⚠️ Analysis Failed",
            "details": str(e)
        }


# ─────────────────────────────────────────────────────────
# Main DocumentExtractor Class
# ─────────────────────────────────────────────────────────
class DocumentExtractor:
    """
    Optimized document intelligence pipeline:
    1. Single Tesseract call → both raw text + confidence
    2. Regex parsing identifies named fields
    3. ELA tamper detection (capped resolution for speed)

    LayoutLMv3 is intentionally disabled: loading a 500MB transformer
    model on every button click was the primary cause of slow analysis.
    Tesseract-only mode is fast and accurate for structured documents.
    """

    def __init__(self):
        # LayoutLMv3 disabled for speed — transformer model load is too slow
        # for interactive use. Re-enable below if you have a GPU + preloaded model.
        self._layoutlm_available = False

    def extract_fields(self, image_bytes: bytes) -> dict:
        """
        Main extraction method. Returns structured dict with:
        - status, engine used
        - extracted_fields (name, DOB, ID, etc.)
        - raw_text from OCR
        - tamper_analysis result
        """
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

        # ── Single OCR call → text + confidence ──────────
        raw_text, avg_conf = extract_text_via_ocr(image)
        fields = parse_fields(raw_text)

        # ── Tamper Detection (ELA) ────────────────────────
        tamper = run_ela(image)

        engine = "Tesseract-OCR (Fast Mode)"

        return {
            "status": "Success",
            "engine": engine,
            "ocr_confidence": avg_conf,
            "extracted_fields": fields,
            "raw_text": raw_text[:600] + ("..." if len(raw_text) > 600 else ""),
            "tamper_analysis": tamper,
        }
