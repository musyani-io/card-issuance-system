"""Capture a single image from the configured camera device and save it.

Run this directly from the project root:

    python3 modules/capture_image.py
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import cv2

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import config


def _resolve_capture_path() -> Path:
    capture_dir = Path(config.CAPTURE_DIR)
    capture_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
    filename = f"{config.CAPTURE_OUTPUT_PREFIX}_{timestamp}{config.CAPTURE_IMAGE_EXTENSION}"
    return capture_dir / filename


def _open_capture_device() -> cv2.VideoCapture:
    candidates = list(getattr(config, "CAPTURE_DEVICE_CANDIDATES", [config.CAPTURE_DEVICE]))
    if config.CAPTURE_DEVICE not in candidates:
        candidates.insert(0, config.CAPTURE_DEVICE)

    last_error = None
    for device_path in candidates:
        capture = cv2.VideoCapture(device_path)
        if not capture.isOpened():
            capture.release()
            last_error = device_path
            continue

        capture.set(cv2.CAP_PROP_FRAME_WIDTH, float(config.CAPTURE_WIDTH))
        capture.set(cv2.CAP_PROP_FRAME_HEIGHT, float(config.CAPTURE_HEIGHT))
        capture.set(cv2.CAP_PROP_FPS, float(config.CAPTURE_FPS))
        return capture

    raise RuntimeError(
        f"could not open any capture device from: {', '.join(candidates)}"
        + (f" (last tried: {last_error})" if last_error is not None else "")
    )


def _warm_up_capture(capture: cv2.VideoCapture) -> None:
    for _ in range(int(config.CAPTURE_WARMUP_FRAMES)):
        capture.read()


def capture_image() -> Path:
    capture_path = _resolve_capture_path()
    capture = _open_capture_device()

    try:
        _warm_up_capture(capture)
        ok, frame = capture.read()
        if not ok or frame is None:
            raise RuntimeError("failed to read a frame from the capture device")

        frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)

        if not cv2.imwrite(str(capture_path), frame):
            raise RuntimeError(f"failed to write image to {capture_path}")
    finally:
        capture.release()

    return capture_path


def main() -> int:
    try:
        output_path = capture_image()
    except Exception as exc:
        print(f"capture failed: {exc}", file=sys.stderr)
        return 1

    print(f"captured image saved to: {output_path}")
    print(f"source device: {config.CAPTURE_DEVICE}")
    print(f"phone label: {config.PHONE_CAMERA_LABEL}")
    print(f"phone media path: {config.PHONE_MEDIA_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())