"""OCR preprocessing helpers and runnable OCR pipeline for the kiosk-brain project.

This module provides the image cleanup and Tesseract helpers used by the card
detection pipeline. When run directly, it first captures a fresh image, then
processes the latest file from the captures folder and prints the extracted
registration number.
"""

from __future__ import annotations

import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import config

try:
    import pytesseract
except Exception:  # pragma: no cover - optional runtime dependency
    pytesseract = None


REG_NUMBER_PATTERNS = (
    re.compile(r"\b\d{4}-\d{2}-\d{5}\b"),
    re.compile(r"\bT/UDSM/\d{4}/\d{4}\b", re.IGNORECASE),
)


def _format_compact_registration_number(digits: str) -> str | None:
    """Format a compact 11-digit registration number into XXXX-XX-XXXXX."""

    if len(digits) == 11:
        return f"{digits[:4]}-{digits[4:6]}-{digits[6:]}"
    return None


def convert_to_grayscale(image: np.ndarray) -> np.ndarray:
    """Convert a BGR or grayscale image to a single-channel grayscale image."""

    if image is None:
        raise ValueError("image cannot be None")

    if image.ndim == 2:
        return image.copy()

    if image.ndim != 3:
        raise ValueError(f"expected a 2D or 3D image array, got {image.ndim}D")

    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)


def apply_adaptive_threshold(image: np.ndarray) -> np.ndarray:
    """Apply Gaussian adaptive thresholding to a grayscale image."""

    if image is None:
        raise ValueError("image cannot be None")

    grayscale = convert_to_grayscale(image)
    gk = tuple(config.OCR_PREPROCESS["gaussian_ksize"])
    denoised = cv2.GaussianBlur(grayscale, gk, 0)

    block = int(config.OCR_PREPROCESS["adaptive_block_size"])
    if block <= 1:
        block = 3
    if block % 2 == 0:
        block += 1
    c = int(config.OCR_PREPROCESS["adaptive_C"])

    thresholded = cv2.adaptiveThreshold(
        denoised,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        block,
        c,
    )

    mk = tuple(config.OCR_PREPROCESS["morph_kernel"])
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, mk)
    thresholded = cv2.morphologyEx(thresholded, cv2.MORPH_OPEN, kernel)
    return thresholded


def load_image(image_path: str | Path) -> np.ndarray:
    """Load an image from disk in BGR format."""

    path = Path(image_path)
    image = cv2.imread(str(path))
    if image is None:
        raise FileNotFoundError(f"could not read image: {path}")
    return image


def save_grayscale_preview(
    image_path: str | Path, output_dir: str | Path
) -> dict[str, Path]:
    """Save the original image, grayscale image, and a side-by-side preview."""

    source_path = Path(image_path)
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)

    original = load_image(source_path)
    grayscale = convert_to_grayscale(original)

    original_path = destination / "original.jpg"
    grayscale_path = destination / "grayscale.jpg"
    preview_path = destination / "preview.jpg"
    info_path = destination / "details.txt"

    cv2.imwrite(str(original_path), original)
    cv2.imwrite(str(grayscale_path), grayscale)

    grayscale_bgr = cv2.cvtColor(grayscale, cv2.COLOR_GRAY2BGR)
    preview = cv2.hconcat([original, grayscale_bgr])
    cv2.imwrite(str(preview_path), preview)

    info_path.write_text(
        "\n".join(
            [
                f"source={source_path.name}",
                f"original_shape={original.shape}",
                f"grayscale_shape={grayscale.shape}",
                "stage=1.2.1 grayscale conversion",
            ]
        ),
        encoding="utf-8",
    )

    return {
        "original": original_path,
        "grayscale": grayscale_path,
        "preview": preview_path,
        "details": info_path,
    }


def save_threshold_preview(
    image_path: str | Path, output_dir: str | Path
) -> dict[str, Path]:
    """Save the grayscale and adaptive-threshold images plus a side-by-side preview."""

    source_path = Path(image_path)
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)

    original = load_image(source_path)
    grayscale = convert_to_grayscale(original)
    thresholded = apply_adaptive_threshold(grayscale)
    gk = tuple(config.OCR_PREPROCESS["gaussian_ksize"])
    block = int(config.OCR_PREPROCESS["adaptive_block_size"])
    if block <= 1:
        block = 3
    if block % 2 == 0:
        block += 1
    c = int(config.OCR_PREPROCESS["adaptive_C"])
    mk = tuple(config.OCR_PREPROCESS["morph_kernel"])

    grayscale_path = destination / "grayscale.jpg"
    threshold_path = destination / "adaptive_threshold.jpg"
    preview_path = destination / "adaptive_threshold_preview.jpg"
    info_path = destination / "threshold_details.txt"

    cv2.imwrite(str(grayscale_path), grayscale)
    cv2.imwrite(str(threshold_path), thresholded)

    grayscale_bgr = cv2.cvtColor(grayscale, cv2.COLOR_GRAY2BGR)
    threshold_bgr = cv2.cvtColor(thresholded, cv2.COLOR_GRAY2BGR)
    preview = cv2.hconcat([grayscale_bgr, threshold_bgr])
    cv2.imwrite(str(preview_path), preview)

    info_path.write_text(
        "\n".join(
            [
                f"source={source_path.name}",
                f"grayscale_shape={grayscale.shape}",
                f"threshold_shape={thresholded.shape}",
                "stage=1.2.2 gaussian adaptive thresholding",
                f"preprocess=gaussian_blur_{gk[0]}x{gk[1]}",
                f"adaptive_block_size={block}",
                f"adaptive_c={c}",
                f"postprocess=morph_open_{mk[0]}x{mk[1]}",
            ]
        ),
        encoding="utf-8",
    )

    return {
        "grayscale": grayscale_path,
        "threshold": threshold_path,
        "preview": preview_path,
        "details": info_path,
    }


def apply_pre_ocr_enhancement(image: np.ndarray) -> np.ndarray:
    """Apply mild blur followed by a sharpening kernel to an image.

    This is Task 1.2.6: reduces small noise while preserving character edges.
    Reads `PRE_OCR` settings from `config` and returns a BGR or grayscale image
    with the same number of channels as the input.
    """

    if image is None:
        raise ValueError("image cannot be None")

    # preserve input shape/channels
    orig_ndim = image.ndim

    # Apply small Gaussian blur
    bk = tuple(config.PRE_OCR["blur_ksize"])
    blurred = cv2.GaussianBlur(image, bk, 0)

    # Apply sharpening kernel
    kernel = np.array(config.PRE_OCR["sharpen_kernel"], dtype=np.float32)
    # filter2D works on multi-channel images as well
    sharpened = cv2.filter2D(blurred, -1, kernel)

    # Clip to valid uint8 range and cast back
    sharpened = np.clip(sharpened, 0, 255).astype("uint8")

    # Return image with same dimensionality as input
    if orig_ndim == 2 and sharpened.ndim == 3:
        return cv2.cvtColor(sharpened, cv2.COLOR_BGR2GRAY)
    return sharpened


def perform_ocr(
    image: np.ndarray, *, psm: int | None = None, whitelist: str | None = None
) -> dict:
    """Run Tesseract OCR on `image` and return text and confidence metadata.

    - `image` may be grayscale, BGR, or binarized. The function will call
      `pytesseract.image_to_data` and compute average confidence where available.
    - Returns: {"text": str, "mean_confidence": float or None, "raw": str}
    """

    if pytesseract is None:
        raise RuntimeError("pytesseract not available in this environment")

    # Ensure image is in a format pytesseract accepts (BGR -> RGB)
    img = image
    if img.ndim == 3 and img.shape[2] == 3:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    config_parts = []
    if psm is not None:
        config_parts.append(f"--psm {int(psm)}")
    if whitelist:
        # tessedit_char_whitelist expects no spaces
        wl = whitelist.replace(" ", "")
        config_parts.append(f"-c tessedit_char_whitelist={wl}")

    config_str = " ".join(config_parts)

    # Get plain text
    text = pytesseract.image_to_string(img, config=config_str).strip()

    # Get detailed data to compute confidences
    data = pytesseract.image_to_data(
        img, config=config_str, output_type=pytesseract.Output.DICT
    )
    confs = []
    for conf in data.get("conf", []):
        try:
            c = float(conf)
        except Exception:
            continue
        # Tesseract uses -1 for blanks; skip those
        if c >= 0:
            confs.append(c)

    mean_conf = float(sum(confs) / len(confs)) if confs else None
    return {"text": text, "mean_confidence": mean_conf, "raw_data": data}


def _run_capture_script() -> Path:
    script_path = PROJECT_ROOT / "modules" / "capture_image.py"
    subprocess.run([sys.executable, str(script_path)], check=True, cwd=PROJECT_ROOT)

    capture_dir = Path(config.CAPTURE_DIR)
    if not capture_dir.exists():
        raise FileNotFoundError(f"capture directory does not exist: {capture_dir}")

    return capture_dir


def _latest_capture_image(capture_dir: Path) -> Path:
    candidates = [
        path
        for path in capture_dir.iterdir()
        if path.is_file() and path.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp"}
    ]
    if not candidates:
        raise FileNotFoundError(f"no captured images found in {capture_dir}")

    return max(candidates, key=lambda path: (path.stat().st_mtime, path.name))


def extract_registration_number(text: str) -> str | None:
    """Extract a likely registration number from OCR text."""

    if not text:
        return None

    normalized = text.upper().replace(" ", "")
    for pattern in REG_NUMBER_PATTERNS:
        match = pattern.search(normalized)
        if match:
            return match.group(0)

    compact_digits = re.sub(r"\D", "", normalized)
    formatted = _format_compact_registration_number(compact_digits)
    if formatted:
        return formatted

    return None


def run_ocr_pipeline() -> str:
    """Capture a fresh image, process the latest capture, and return reg number."""

    capture_dir = _run_capture_script()
    latest_image = _latest_capture_image(capture_dir)

    from modules.card_detector import save_roi_preview

    pipeline_output_dir = Path(config.PROCESS_OUTPUT_DIR) / latest_image.stem
    pipeline_output_dir.mkdir(parents=True, exist_ok=True)

    roi_outputs = save_roi_preview(latest_image, pipeline_output_dir)

    ocr_inputs = [
        roi_outputs.get("roi"),
        roi_outputs.get("roi_preocr"),
        roi_outputs.get("threshold"),
        roi_outputs.get("grayscale"),
    ]
    ocr_inputs = [path for path in ocr_inputs if path is not None and path.exists()]

    if not ocr_inputs:
        raise FileNotFoundError("no OCR input images were produced by the ROI pipeline")

    whitelist = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789/-"
    last_text = ""
    last_confidence = None

    for candidate_path in ocr_inputs:
        image = cv2.imread(str(candidate_path))
        if image is None:
            continue

        for psm in (7, 8):
            result = perform_ocr(image, psm=psm, whitelist=whitelist)
            text = result.get("text", "")
            registration_number = extract_registration_number(text)
            if registration_number:
                print(f"latest capture: {latest_image}")
                print(f"ocr input: {candidate_path.name}")
                print(f"registration number: {registration_number}")
                return registration_number

            last_text = text
            last_confidence = result.get("mean_confidence")

    raise RuntimeError(
        "could not extract a registration number from the latest capture "
        f"{latest_image}. Last OCR text={last_text!r}, confidence={last_confidence}"
    )


def main() -> int:
    try:
        run_ocr_pipeline()
    except Exception as exc:
        print(f"ocr pipeline failed: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
