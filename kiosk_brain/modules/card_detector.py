"""Card detection helpers for the OCR pipeline.

This module finds the largest card-like contour in a photo and returns the
corner points in a consistent order. It also provides a convenience function
to save a visualisation for per-sample inspection during development.
"""

from __future__ import annotations

from pathlib import Path
import math

import cv2
import numpy as np


def _order_points(pts: np.ndarray) -> np.ndarray:
    """Order four points as top-left, top-right, bottom-right, bottom-left."""

    rect = np.zeros((4, 2), dtype="float32")

    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]  # top-left has smallest sum
    rect[2] = pts[np.argmax(s)]  # bottom-right has largest sum

    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]  # top-right has smallest diff
    rect[3] = pts[np.argmax(diff)]  # bottom-left has largest diff

    return rect


def detect_card_contour(image: np.ndarray) -> tuple[np.ndarray, dict]:
    """Detect a 4-point card contour in `image` (BGR or grayscale).

    Returns an array of shape (4,2) with points in TL, TR, BR, BL order.
    If detection fails, raises RuntimeError.
    """

    if image is None:
        raise ValueError("image cannot be None")

    # Record original image area (for metadata) and normalize to gray
    orig_h, orig_w = image.shape[:2]
    orig_image_area = orig_h * orig_w
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image

    # Scale-normalization (work on a predictable width to make thresholds stable)
    h, w = gray.shape[:2]
    scale = 1.0
    target_w = 1000
    if w > target_w:
        scale = target_w / float(w)
        gray = cv2.resize(gray, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)

    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edged = cv2.Canny(blurred, 50, 150)

    # Morphological closing + dilation to join broken edges
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    edged = cv2.morphologyEx(edged, cv2.MORPH_CLOSE, kernel)
    edged = cv2.dilate(edged, kernel, iterations=1)

    contours_info = cv2.findContours(edged, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours = contours_info[0] if len(contours_info) == 2 else contours_info[1]

    # Sort by contour area, descending
    contours = sorted(contours, key=cv2.contourArea, reverse=True)

    image_area = gray.shape[0] * gray.shape[1]
    min_area = max(1000, int(image_area * 0.03))  # at least 3% of image area
    max_area = int(image_area * 0.9)

    expected_ratio = 88.0 / 55.0
    aspect_tolerance = 0.25  # 25% tolerance

    used_fallback = False

    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < min_area or area > max_area:
            continue

        # perimeter-based polygon approximation
        peri = cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, 0.02 * peri, True)

        # compute a stable rectangle from the contour for aspect checking
        rect = cv2.minAreaRect(cnt)
        box_pts = cv2.boxPoints(rect).reshape(4, 2).astype("float32")
        width, height = rect[1]
        if width == 0 or height == 0:
            continue

        aspect_ratio = max(width, height) / min(width, height)

        if abs(aspect_ratio - expected_ratio) > aspect_tolerance:
            # not card-like aspect
            continue

        # prefer quadrilateral approximations but fall back to minAreaRect box
        if approx.shape[0] == 4:
            pts = approx.reshape(4, 2).astype("float32")
            ordered = _order_points(pts)
            method = "approx"
        else:
            ordered = _order_points(box_pts)
            method = "minAreaRect"

        # rescale points back to original image coordinates if we resized
        if scale != 1.0:
            ordered = ordered / scale

        # compute card properties in original coordinates
        props = get_card_info(ordered)
        meta = {
            "method": method,
            "used_fallback": False,
            "scale": scale,
            "card_width": float(props["width"]),
            "card_height": float(props["height"]),
            "card_aspect_ratio": float(props["aspect_ratio"]),
            "card_area": float(props["area"]),
            "image_area": float(orig_image_area),
        }

        return ordered, meta

    # Fallback: if no contour passed filters, attempt largest contour -> minAreaRect
    if contours:
        used_fallback = True
        rect = cv2.minAreaRect(contours[0])
        box_pts = cv2.boxPoints(rect).reshape(4, 2).astype("float32")
        ordered = _order_points(box_pts)
        if scale != 1.0:
            ordered = ordered / scale

        props = get_card_info(ordered)
        meta = {
            "method": "fallback_minAreaRect",
            "used_fallback": True,
            "scale": scale,
            "card_width": float(props["width"]),
            "card_height": float(props["height"]),
            "card_aspect_ratio": float(props["aspect_ratio"]),
            "card_area": float(props["area"]),
            "image_area": float(orig_image_area),
        }

        return ordered, meta

    raise RuntimeError("could not detect card contour")


def draw_detection_overlay(image: np.ndarray, corners: np.ndarray) -> np.ndarray:
    """Return a BGR copy of `image` with the detected corners and outline drawn."""

    vis = image.copy()
    if vis.ndim == 2:
        vis = cv2.cvtColor(vis, cv2.COLOR_GRAY2BGR)

    pts = corners.reshape(4, 2).astype(int)
    cv2.polylines(vis, [pts], isClosed=True, color=(0, 255, 0), thickness=3)

    for i, (x, y) in enumerate(pts):
        cv2.circle(vis, (int(x), int(y)), 8, (0, 0, 255), -1)
        cv2.putText(vis, str(i + 1), (int(x) + 8, int(y) - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 0, 0), 2)

    return vis


def get_card_info(corners: np.ndarray) -> dict:
    """
    Calculate card properties from corner points.

    Returns width, height, aspect_ratio, area, center.
    """
    width_top = np.linalg.norm(corners[0] - corners[1])
    width_bottom = np.linalg.norm(corners[3] - corners[2])
    width = (width_top + width_bottom) / 2

    height_left = np.linalg.norm(corners[0] - corners[3])
    height_right = np.linalg.norm(corners[1] - corners[2])
    height = (height_left + height_right) / 2

    center = np.mean(corners, axis=0)

    return {
        "width": width,
        "height": height,
        "aspect_ratio": (width / height) if height > 0 else 0,
        "area": width * height,
        "center": tuple(center.astype(int)),
    }


def save_detection_preview(image_path: str | Path, output_dir: str | Path) -> dict[str, Path]:
    """Load `image_path`, detect card, and write visual outputs to `output_dir`.

    Returns paths for 'original', 'detection', and 'details'.
    """

    source = Path(image_path)
    dest = Path(output_dir)
    dest.mkdir(parents=True, exist_ok=True)

    image = cv2.imread(str(source))
    if image is None:
        raise FileNotFoundError(f"could not read image: {source}")

    try:
        result = detect_card_contour(image)
        if isinstance(result, tuple):
            corners, meta = result
        else:
            corners = result
            meta = {}

        overlay = draw_detection_overlay(image, corners)

        original_path = dest / "original.jpg"
        detection_path = dest / "detection.jpg"
        info_path = dest / "detection_details.txt"

        cv2.imwrite(str(original_path), image)
        cv2.imwrite(str(detection_path), overlay)

        lines = [f"source={source.name}", f"original_shape={image.shape}"]
        for idx, (x, y) in enumerate(corners, start=1):
            lines.append(f"pt{idx}={float(x):.2f},{float(y):.2f}")
        lines.append("stage=1.2.1 card detection")
        # Write metadata if available
        if meta:
            lines.append(f"method={meta.get('method')}")
            lines.append(f"used_fallback={meta.get('used_fallback')}")
            lines.append(f"card_width={meta.get('card_width')}")
            lines.append(f"card_height={meta.get('card_height')}")
            lines.append(f"card_aspect_ratio={meta.get('card_aspect_ratio')}")
            lines.append(f"card_area={meta.get('card_area')}")
            lines.append(f"image_area={meta.get('image_area')}")
        info_path.write_text("\n".join(lines), encoding="utf-8")

        return {"original": original_path, "detection": detection_path, "details": info_path}

    except Exception as exc:  # keep simple for development; caller can inspect details file
        err_path = dest / "detection_error.txt"
        err_path.write_text(str(exc), encoding="utf-8")
        raise
