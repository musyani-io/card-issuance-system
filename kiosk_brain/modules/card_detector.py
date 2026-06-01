"""Card detection helpers for the OCR pipeline.

This module finds the largest card-like contour in a photo and returns the
corner points in a consistent order. It also provides a convenience function
to save a visualisation for per-sample inspection during development.
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

import config
from modules.ocr import apply_adaptive_threshold, convert_to_grayscale


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
    target_w = int(config.CARD_DETECTION["target_width"])
    if w > target_w:
        scale = target_w / float(w)
        gray = cv2.resize(gray, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)

    # Blur + Canny using config values
    blur_ksize = tuple(config.CARD_DETECTION["blur_ksize"])
    blurred = cv2.GaussianBlur(gray, blur_ksize, 0)

    c1 = int(config.CARD_DETECTION["canny_threshold1"])
    c2 = int(config.CARD_DETECTION["canny_threshold2"])
    edged = cv2.Canny(blurred, c1, c2)

    # Morphological closing + dilation to join broken edges
    mk = tuple(config.CARD_DETECTION["morph_kernel"])
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, mk)
    edged = cv2.morphologyEx(edged, cv2.MORPH_CLOSE, kernel)
    edged = cv2.dilate(edged, kernel, iterations=int(config.CARD_DETECTION["dilate_iterations"]))

    contours_info = cv2.findContours(edged, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours = contours_info[0] if len(contours_info) == 2 else contours_info[1]

    # Sort by contour area, descending
    contours = sorted(contours, key=cv2.contourArea, reverse=True)

    image_area = gray.shape[0] * gray.shape[1]
    min_area_abs = int(config.CARD_DETECTION["min_area_abs"])
    min_area_ratio = float(config.CARD_DETECTION["min_area_ratio"])
    min_area = max(min_area_abs, int(image_area * min_area_ratio))
    max_area = int(image_area * float(config.CARD_DETECTION["max_area_ratio"]))

    expected_ratio = float(config.CARD_DETECTION["expected_aspect_ratio"])
    aspect_tolerance = float(config.CARD_DETECTION["aspect_ratio_tolerance"])

    used_fallback = False

    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < min_area or area > max_area:
            continue

        # perimeter-based polygon approximation
        peri = cv2.arcLength(cnt, True)
        approx_eps = float(config.CARD_DETECTION["approx_epsilon"])
        approx = cv2.approxPolyDP(cnt, approx_eps * peri, True)

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


def warp_card(image: np.ndarray, corners: np.ndarray, output_size: tuple[int, int] | None = None) -> np.ndarray:
    """Apply perspective transform to extract a flattened card image.

    `corners` should be in TL, TR, BR, BL order or will be ordered.
    `output_size` is (width, height) in pixels for the destination card image.
    """

    if image is None:
        raise ValueError("image cannot be None")

    pts = corners.astype("float32")
    rect = _order_points(pts)
    (tl, tr, br, bl) = rect

    if output_size is None:
        output_size = tuple(config.PERSPECTIVE["output_size"])
    dst_w, dst_h = output_size

    dst = np.array(
        [[0, 0], [dst_w - 1, 0], [dst_w - 1, dst_h - 1], [0, dst_h - 1]], dtype="float32"
    )

    M = cv2.getPerspectiveTransform(rect, dst)
    warped = cv2.warpPerspective(image, M, (dst_w, dst_h))
    return warped


def save_perspective_preview(image_path: str | Path, output_dir: str | Path, output_size: tuple[int, int] | None = None) -> dict[str, Path]:
    """Detect card, warp it to `output_size`, and write flattened previews.

    Returns paths for 'original', 'flattened', 'preview', and 'details'.
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

        warped = warp_card(image, corners, output_size=output_size)

        original_path = dest / "original.jpg"
        flattened_path = dest / "flattened.jpg"
        preview_path = dest / "flattened_preview.jpg"
        info_path = dest / "perspective_details.txt"

        cv2.imwrite(str(original_path), image)
        cv2.imwrite(str(flattened_path), warped)

        warped_bgr = warped if warped.ndim == 3 else cv2.cvtColor(warped, cv2.COLOR_GRAY2BGR)
        preview = cv2.hconcat([cv2.resize(image, (warped_bgr.shape[1], warped_bgr.shape[0])), warped_bgr])
        cv2.imwrite(str(preview_path), preview)

        lines = [f"source={source.name}", f"original_shape={image.shape}", f"flattened_shape={warped.shape}", "stage=1.2.2 perspective correction"]
        if meta:
            for k, v in meta.items():
                lines.append(f"{k}={v}")

        info_path.write_text("\n".join(lines), encoding="utf-8")

        return {"original": original_path, "flattened": flattened_path, "preview": preview_path, "details": info_path}

    except Exception as exc:
        err_path = dest / "perspective_error.txt"
        err_path.write_text(str(exc), encoding="utf-8")
        raise


def crop_registration_roi_from_flat(flattened: np.ndarray, roi_rel: tuple[float, float, float, float] = None) -> np.ndarray:
    """Crop a region of interest from a flattened card image.

    roi_rel = (x, y, w, h) in relative fractions of flattened width/height.
    Returns the cropped ROI image (BGR or grayscale same as input).
    """
    if flattened is None:
        raise ValueError("flattened image cannot be None")

    h, w = flattened.shape[:2]
    if roi_rel is None:
        roi_rel = tuple(config.ROI["default"])
    rx, ry, rw, rh = roi_rel
    x = max(0, int(round(rx * w)))
    y = max(0, int(round(ry * h)))
    ww = max(1, int(round(rw * w)))
    hh = max(1, int(round(rh * h)))

    x2 = min(w, x + ww)
    y2 = min(h, y + hh)

    return flattened[y:y2, x:x2]


def save_roi_preview(image_path: str | Path, output_dir: str | Path, roi_rel: tuple[float, float, float, float] = None) -> dict[str, Path]:
    """Detect, flatten, crop ROI (registration number), and save previews + details."""

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

        warped = warp_card(image, corners, output_size=tuple(config.PERSPECTIVE["output_size"]))
        roi = crop_registration_roi_from_flat(warped, roi_rel=roi_rel)
        # determine which ROI was actually used (None -> config default)
        used_roi_rel = roi_rel if roi_rel is not None else tuple(config.ROI["default"])

        gray = convert_to_grayscale(roi)
        thresh = apply_adaptive_threshold(gray)

        original_path = dest / "original.jpg"
        flattened_path = dest / "flattened.jpg"
        roi_path = dest / "roi.jpg"
        roi_gray_path = dest / "roi_grayscale.jpg"
        roi_thresh_path = dest / "roi_threshold.jpg"
        preview_path = dest / "roi_preview.jpg"
        info_path = dest / "roi_details.txt"

        cv2.imwrite(str(original_path), image)
        cv2.imwrite(str(flattened_path), warped)
        cv2.imwrite(str(roi_path), roi)
        cv2.imwrite(str(roi_gray_path), gray)
        cv2.imwrite(str(roi_thresh_path), thresh)

        gray_bgr = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
        thresh_bgr = cv2.cvtColor(thresh, cv2.COLOR_GRAY2BGR)
        preview = cv2.hconcat([gray_bgr, thresh_bgr])
        cv2.imwrite(str(preview_path), preview)

        lines = [f"source={source.name}", f"flattened_shape={warped.shape}", f"roi_rel={used_roi_rel}", f"roi_shape={roi.shape}", "stage=1.2.5 roi crop and preprocess"]
        if meta:
            for k, v in meta.items():
                lines.append(f"{k}={v}")

        info_path.write_text("\n".join(lines), encoding="utf-8")

        return {"original": original_path, "flattened": flattened_path, "roi": roi_path, "grayscale": roi_gray_path, "threshold": roi_thresh_path, "preview": preview_path, "details": info_path}

    except Exception as exc:
        err_path = dest / "roi_error.txt"
        err_path.write_text(str(exc), encoding="utf-8")
        raise


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
