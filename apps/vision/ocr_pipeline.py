"""OCR label-recognition pipeline.

Preprocessing (OpenCV/Pillow) -> Tesseract OCR (pytesseract) -> regex/
heuristic field extraction, exactly as scoped in Chapters 2-3 of the
project report. This module is assistive only: every field it returns is
presented to the user for review/edit before anything is saved (see
apps.vision.views.OcrScanView and the frontend review screen) — it never
writes to the inventory on its own.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date

import cv2
import numpy as np
import pytesseract
from dateutil import parser as dateutil_parser
from PIL import Image
from pytesseract import Output

# --- Confidence acceptance threshold (thesis 3.5.4: theta = 0.80) ----------
CONFIDENCE_THRESHOLD = 0.80

# --- Regex / keyword dictionaries -------------------------------------------
CAS_RE = re.compile(r"\b(\d{2,7}-\d{2}-\d)\b")
HCODE_RE = re.compile(r"\bH[234]\d{2}[A-Za-z]?\b")
SIGNAL_WORD_RE = re.compile(r"\b(DANGER|WARNING)\b", re.IGNORECASE)
HAZARD_KEYWORDS = [
    "FLAMMABLE", "CORROSIVE", "TOXIC", "OXIDIZER", "OXIDIZING", "IRRITANT",
    "CARCINOGEN", "REACTIVE", "EXPLOSIVE", "HARMFUL", "SENSITIZER",
]
EXPIRY_CONTEXT_RE = re.compile(r"(EXP\b|EXPIRY|EXPIRES|USE BY|BEST BEFORE|BBE)", re.IGNORECASE)
YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")
MANUFACTURER_RE = re.compile(
    r"(?:Distributed by|Manufactured by|Made by|Mfr\.?)[:\s]+([A-Za-z0-9 ,.\-&]{3,60})",
    re.IGNORECASE,
)


@dataclass
class Word:
    text: str
    conf: float  # 0-100, Tesseract's native scale
    line_key: tuple


@dataclass
class ExtractionResult:
    raw_text: str = ""
    name: str = ""
    cas_number: str = ""
    cas_checksum_valid: bool | None = None
    expiry_date: str | None = None  # ISO YYYY-MM-DD
    manufacturer: str = ""
    ghs_codes: list[str] = field(default_factory=list)
    hazard_keywords: list[str] = field(default_factory=list)
    confidence: dict[str, float] = field(default_factory=dict)


# --- Preprocessing (OpenCV / Pillow) ----------------------------------------

def preprocess_image(pil_image: Image.Image) -> np.ndarray:
    """Grayscale -> denoise -> adaptive threshold -> deskew.

    Returns a binarized numpy array ready for Tesseract.
    """
    rgb = np.array(pil_image.convert("RGB"))
    bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)

    # Cap resolution — very large phone photos slow Tesseract down for no
    # accuracy benefit; very small ones get upscaled since Tesseract does
    # better with more pixels per character.
    h, w = gray.shape
    target_w = 1600
    if w != target_w:
        scale = target_w / w
        gray = cv2.resize(gray, (target_w, int(h * scale)), interpolation=cv2.INTER_CUBIC if scale > 1 else cv2.INTER_AREA)

    denoised = cv2.fastNlMeansDenoising(gray, h=10)
    thresh = cv2.adaptiveThreshold(
        denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 11,
    )
    return _deskew(thresh)


def _deskew(binary_img: np.ndarray) -> np.ndarray:
    """Rotates the image so detected text runs horizontally.

    Estimates skew from the minimum-area bounding rectangle of the dark
    (text) pixels. Skips rotation when there isn't enough signal to trust
    the estimate, or when the estimated skew is negligible.
    """
    text_pixels = np.column_stack(np.where(binary_img < 255))
    if text_pixels.shape[0] < 50:
        return binary_img

    angle = cv2.minAreaRect(text_pixels.astype(np.float32))[-1]
    angle = -(90 + angle) if angle < -45 else -angle
    if abs(angle) < 0.5:
        return binary_img

    h, w = binary_img.shape[:2]
    matrix = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
    return cv2.warpAffine(
        binary_img, matrix, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE,
    )


# --- OCR ---------------------------------------------------------------------

def run_ocr(processed: np.ndarray) -> tuple[str, list[Word], dict[tuple, list[Word]]]:
    """Runs Tesseract, returning raw text, a flat word list (with
    per-word confidence), and words grouped by line for name extraction."""
    image = Image.fromarray(processed)
    data = pytesseract.image_to_data(image, output_type=Output.DICT)

    words: list[Word] = []
    lines: dict[tuple, list[Word]] = {}
    for i in range(len(data["text"])):
        text = data["text"][i].strip()
        conf = float(data["conf"][i])
        if not text or conf < 0:
            continue
        line_key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
        w = Word(text=text, conf=conf, line_key=line_key)
        words.append(w)
        lines.setdefault(line_key, []).append(w)

    raw_text = "\n".join(" ".join(w.text for w in ws) for ws in lines.values())
    return raw_text, words, lines


# --- Field extraction ---------------------------------------------------------

def _cas_checksum_valid(cas: str) -> bool:
    digits = cas.replace("-", "")
    if len(digits) < 4 or not digits.isdigit():
        return False
    check_digit = int(digits[-1])
    body = digits[:-1]
    total = sum(int(d) * (i + 1) for i, d in enumerate(reversed(body)))
    return total % 10 == check_digit


def _confidence_for_text(candidate: str, words: list[Word]) -> float:
    """Mean confidence (0-1) of the OCR words that make up `candidate`,
    per thesis 3.5.4. Matches case-insensitively on whole tokens."""
    if not candidate:
        return 0.0
    tokens = {t.lower() for t in re.split(r"[\s,]+", candidate) if t}
    matched = [w.conf for w in words if w.text.strip(".,;:").lower() in tokens]
    if not matched:
        return 0.0
    return round((sum(matched) / len(matched)) / 100, 3)


def _extract_cas(raw_text: str, words: list[Word]) -> tuple[str, float | None, bool | None]:
    match = CAS_RE.search(raw_text)
    if not match:
        return "", None, None
    cas = match.group(1)
    valid = _cas_checksum_valid(cas)
    conf = _confidence_for_text(cas, words)
    # Shape matches but the check digit fails — very likely a digit misread
    # by the OCR engine (e.g. 8 <-> B, 0 <-> O). Still surface it (assistive,
    # not autonomous — the user can correct it), just flag lower confidence.
    if not valid:
        conf *= 0.5
    return cas, conf, valid


def _extract_expiry(raw_text: str) -> tuple[str | None, float]:
    lines = [l for l in raw_text.splitlines() if not CAS_RE.search(l)]
    context_lines = [l for l in lines if EXPIRY_CONTEXT_RE.search(l)]
    for candidate_lines, base_conf in ((context_lines, 0.9), (lines, 0.6)):
        for line in candidate_lines:
            if not YEAR_RE.search(line):
                continue
            try:
                parsed = dateutil_parser.parse(line, fuzzy=True, dayfirst=False)
            except (ValueError, OverflowError):
                continue
            if not (date(2000, 1, 1) <= parsed.date() <= date(2100, 1, 1)):
                continue
            return parsed.date().isoformat(), base_conf
    return None, 0.0


def _extract_hazard_signals(raw_text: str) -> tuple[list[str], list[str]]:
    ghs_codes = sorted(set(HCODE_RE.findall(raw_text.upper())))
    upper = raw_text.upper()
    keywords = [w for w in HAZARD_KEYWORDS if w in upper]
    if SIGNAL_WORD_RE.search(raw_text):
        keywords = [SIGNAL_WORD_RE.search(raw_text).group(1).upper()] + keywords
    return ghs_codes, keywords


def _extract_manufacturer(raw_text: str) -> str:
    match = MANUFACTURER_RE.search(raw_text)
    return match.group(1).strip() if match else ""


def _extract_name(lines: dict[tuple, list[Word]], cas: str, expiry_hint: str | None) -> tuple[str, float]:
    """Positional + keyword heuristic (thesis 3.5.1): the longest
    alphabetic-majority line, weighted toward the top of the label, that
    isn't itself a CAS number, date, H-code, or signal-word line."""
    best_line, best_score = None, -1.0
    ordered = list(lines.items())
    total = max(len(ordered), 1)
    for position, (_, words) in enumerate(ordered):
        text = " ".join(w.text for w in words)
        stripped = text.strip()
        if not stripped or CAS_RE.fullmatch(stripped) or HCODE_RE.fullmatch(stripped):
            continue
        if SIGNAL_WORD_RE.fullmatch(stripped):
            continue
        alpha = sum(c.isalpha() for c in stripped)
        if alpha < 3 or alpha / max(len(stripped), 1) < 0.5:
            continue
        position_weight = 1.0 - (position / total) * 0.5  # favor lines near the top
        length_weight = min(len(stripped) / 30, 1.0)
        score = position_weight * 0.6 + length_weight * 0.4
        if score > best_score:
            best_score, best_line, best_words = score, stripped, words
    if not best_line:
        return "", 0.0
    conf = round((sum(w.conf for w in best_words) / len(best_words)) / 100, 3)
    return best_line.title() if best_line.isupper() else best_line, conf


def run_pipeline(pil_image: Image.Image) -> ExtractionResult:
    processed = preprocess_image(pil_image)
    raw_text, words, lines = run_ocr(processed)

    cas, cas_conf, cas_valid = _extract_cas(raw_text, words)
    expiry, expiry_conf = _extract_expiry(raw_text)
    ghs_codes, hazard_keywords = _extract_hazard_signals(raw_text)
    manufacturer = _extract_manufacturer(raw_text)
    name, name_conf = _extract_name(lines, cas, expiry)

    return ExtractionResult(
        raw_text=raw_text,
        name=name,
        cas_number=cas,
        cas_checksum_valid=cas_valid,
        expiry_date=expiry,
        manufacturer=manufacturer,
        ghs_codes=ghs_codes,
        hazard_keywords=hazard_keywords,
        confidence={
            "name": name_conf,
            "cas_number": cas_conf or 0.0,
            "expiry_date": expiry_conf,
        },
    )
