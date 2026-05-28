"""
Anchor-based ROI extraction.

Find a fixed label (anchor text) on the straightened card using OCR,
then derive ROI boxes relative to that anchor.
"""

from typing import Dict, Optional, Tuple
import cv2
import numpy as np
import pytesseract


def _preprocess_for_anchor(image: np.ndarray) -> np.ndarray:
    """Preprocess image to improve anchor text OCR."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    # Increase contrast with adaptive thresholding
    thresh = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 21, 10
    )
    return thresh


def find_anchor_box(
    card_image: np.ndarray,
    anchor_texts: list,
    min_confidence: int = 50,
    psm: int = 6,
    oem: int = 3,
    char_whitelist: str = "ABCDEFGHIJKLMNOPQRSTUVWXYZ: ",
) -> Optional[Tuple[int, int, int, int]]:
    """
    Find anchor label bounding box in the card image.

    Returns:
        (x, y, w, h) of the matched anchor, or None if not found.
    """
    if card_image is None or card_image.size == 0:
        return None

    processed = _preprocess_for_anchor(card_image)

    config = f"--psm {psm} --oem {oem} -c tessedit_char_whitelist={char_whitelist}"
    data = pytesseract.image_to_data(
        processed, config=config, output_type=pytesseract.Output.DICT
    )

    anchor_texts_norm = [t.strip().upper() for t in anchor_texts]

    best = None
    best_conf = -1

    n = len(data["text"])
    for i in range(n):
        text = str(data["text"][i]).strip().upper()
        conf_raw = data["conf"][i]
        if isinstance(conf_raw, (int, float)):
            conf = int(conf_raw)
        else:
            conf_str = str(conf_raw).strip()
            conf = int(conf_str) if conf_str.lstrip("-").isdigit() else -1

        if conf < min_confidence:
            continue

        if text in anchor_texts_norm:
            x = data["left"][i]
            y = data["top"][i]
            w = data["width"][i]
            h = data["height"][i]

            if conf > best_conf:
                best_conf = conf
                best = (x, y, w, h)

    return best


def derive_rois_from_anchor(
    card_image: np.ndarray,
    anchor_box: Tuple[int, int, int, int],
    offsets: Dict[str, Dict[str, float]],
) -> Dict[str, Dict[str, float]]:
    """
    Convert anchor box and offsets into ROI ratios.

    Args:
        card_image: Straightened card image
        anchor_box: (x, y, w, h) anchor position
        offsets: dict of ROI offsets (fractions of card width/height)

    Returns:
        ROI ratios dict compatible with ROI extraction format
    """
    h, w = card_image.shape[:2]
    ax, ay, _, _ = anchor_box

    anchor_x_ratio = ax / w
    anchor_y_ratio = ay / h

    derived = {}
    for name, cfg in offsets.items():
        x_start = anchor_x_ratio + cfg["dx"]
        y_start = anchor_y_ratio + cfg["dy"]
        x_end = x_start + cfg["w"]
        y_end = y_start + cfg["h"]

        # Clamp to [0, 1]
        x_start = max(0.0, min(1.0, x_start))
        y_start = max(0.0, min(1.0, y_start))
        x_end = max(0.0, min(1.0, x_end))
        y_end = max(0.0, min(1.0, y_end))

        derived[name] = {
            "x_start": x_start,
            "x_end": x_end,
            "y_start": y_start,
            "y_end": y_end,
        }

    return derived
