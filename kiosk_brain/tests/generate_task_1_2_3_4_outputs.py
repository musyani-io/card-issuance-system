#!/usr/bin/env python3
"""Run perspective correction then grayscale + adaptive threshold for each sample.

Writes per-sample outputs into tests/outputs/<sample>:
 - flattened.jpg (from perspective)
 - flattened_grayscale.jpg
 - flattened_threshold.jpg
 - flattened_preview.jpg (flattened | grayscale)
 - threshold_preview.jpg (grayscale | threshold)
 - details.txt
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import cv2

from modules.card_detector import detect_card_contour, warp_card, save_perspective_preview
from modules.ocr import convert_to_grayscale, apply_adaptive_threshold


def iter_sample_images(samples_dir: Path) -> list[Path]:
    allowed_suffixes = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}
    return sorted(
        path for path in samples_dir.iterdir() if path.is_file() and path.suffix.lower() in allowed_suffixes
    )


def build_output_root(project_root: Path) -> Path:
    return project_root / "tests" / "outputs"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run perspective -> grayscale -> threshold pipeline for samples")
    parser.add_argument(
        "--samples-dir",
        type=Path,
        default=SCRIPT_DIR / "fixtures" / "ocr_samples",
    )
    parser.add_argument(
        "--outputs-dir",
        type=Path,
        default=build_output_root(PROJECT_ROOT),
    )
    args = parser.parse_args()

    samples_dir = args.samples_dir.resolve()
    outputs_dir = args.outputs_dir.resolve()
    outputs_dir.mkdir(parents=True, exist_ok=True)

    sample_images = iter_sample_images(samples_dir)
    if not sample_images:
        raise FileNotFoundError(f"no image samples found in {samples_dir}")

    print(f"Found {len(sample_images)} sample image(s) in {samples_dir}")
    print(f"Writing outputs to {outputs_dir}\n")

    for sample_path in sample_images:
        sample_output_dir = outputs_dir / sample_path.stem
        sample_output_dir.mkdir(parents=True, exist_ok=True)

        image = cv2.imread(str(sample_path))
        if image is None:
            print(f"Could not read {sample_path}")
            continue

        details = [f"source={sample_path.name}", f"original_shape={image.shape}"]

        try:
            result = detect_card_contour(image)
            if isinstance(result, tuple):
                corners, meta = result
            else:
                corners = result
                meta = {}

            # call warp_card without explicit output_size so it picks `config.PERSPECTIVE`
            warped = warp_card(image, corners)

            flat_path = sample_output_dir / "flattened.jpg"
            flat_gray_path = sample_output_dir / "flattened_grayscale.jpg"
            flat_thresh_path = sample_output_dir / "flattened_threshold.jpg"
            flat_preview = sample_output_dir / "flattened_preview.jpg"
            thresh_preview = sample_output_dir / "threshold_preview.jpg"
            info_path = sample_output_dir / "details.txt"

            cv2.imwrite(str(flat_path), warped)

            grayscale = convert_to_grayscale(warped)
            cv2.imwrite(str(flat_gray_path), grayscale)

            thresholded = apply_adaptive_threshold(grayscale)
            cv2.imwrite(str(flat_thresh_path), thresholded)

            # Previews
            warped_bgr = warped if warped.ndim == 3 else cv2.cvtColor(warped, cv2.COLOR_GRAY2BGR)
            gray_bgr = cv2.cvtColor(grayscale, cv2.COLOR_GRAY2BGR)
            thresh_bgr = cv2.cvtColor(thresholded, cv2.COLOR_GRAY2BGR)

            preview1 = cv2.hconcat([cv2.resize(warped_bgr, (gray_bgr.shape[1], gray_bgr.shape[0])), gray_bgr])
            cv2.imwrite(str(flat_preview), preview1)

            preview2 = cv2.hconcat([gray_bgr, thresh_bgr])
            cv2.imwrite(str(thresh_preview), preview2)

            # details
            if meta:
                for k, v in meta.items():
                    details.append(f"{k}={v}")

            info_path.write_text("\n".join(details), encoding="utf-8")

            print(f"{sample_path.name} -> {sample_output_dir}")
            print(f"  flattened: {flat_path.name}")
            print(f"  grayscale: {flat_gray_path.name}")
            print(f"  threshold: {flat_thresh_path.name}")

        except Exception as exc:
            err_path = sample_output_dir / "pipeline_error.txt"
            err_path.write_text(str(exc), encoding="utf-8")
            print(f"{sample_path.name} -> error: {exc}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
