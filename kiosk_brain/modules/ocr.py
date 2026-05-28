"""
OCR preprocessing helpers for the kiosk-brain project.

This module starts with the Phase 1.2 preprocessing pipeline. For Task 1.2.1,
it converts phone or camera captures into grayscale images so the next OCR
stages can work with a cleaner input.
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np


def convert_to_grayscale(image: np.ndarray) -> np.ndarray:
    """Convert a BGR or grayscale image to a single-channel grayscale image."""

    if image is None:
        raise ValueError("image cannot be None")

    if image.ndim == 2:
        return image.copy()

    if image.ndim != 3:
        raise ValueError(f"expected a 2D or 3D image array, got {image.ndim}D")

    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)


def load_image(image_path: str | Path) -> np.ndarray:
    """Load an image from disk in BGR format."""

    path = Path(image_path)
    image = cv2.imread(str(path))
    if image is None:
        raise FileNotFoundError(f"could not read image: {path}")
    return image


def save_grayscale_preview(image_path: str | Path, output_dir: str | Path) -> dict[str, Path]:
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
