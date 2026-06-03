#!/usr/bin/env python3
"""Generate perspective-corrected outputs for Task 1.2.2."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.card_detector import save_perspective_preview


def iter_sample_images(samples_dir: Path) -> list[Path]:
    allowed_suffixes = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}
    return sorted(
        path for path in samples_dir.iterdir() if path.is_file() and path.suffix.lower() in allowed_suffixes
    )


def build_output_root(project_root: Path) -> Path:
    return project_root / "tests" / "outputs"


def main() -> int:
    parser = argparse.ArgumentParser(description="Create perspective-corrected outputs for Task 1.2.2.")
    parser.add_argument(
        "--samples-dir",
        type=Path,
        default=SCRIPT_DIR / "fixtures" / "ocr_samples",
        help="Directory containing sample card images.",
    )
    parser.add_argument(
        "--outputs-dir",
        type=Path,
        default=build_output_root(PROJECT_ROOT),
        help="Directory where per-sample output folders will be written.",
    )
    args = parser.parse_args()

    samples_dir = args.samples_dir.resolve()
    outputs_dir = args.outputs_dir.resolve()
    outputs_dir.mkdir(parents=True, exist_ok=True)

    if not samples_dir.exists():
        raise FileNotFoundError(f"sample directory not found: {samples_dir}")

    sample_images = iter_sample_images(samples_dir)
    if not sample_images:
        raise FileNotFoundError(f"no image samples found in {samples_dir}")

    print(f"Found {len(sample_images)} sample image(s) in {samples_dir}")
    print(f"Writing outputs to {outputs_dir}\n")

    for sample_path in sample_images:
        sample_output_dir = outputs_dir / sample_path.stem
        paths = save_perspective_preview(sample_path, sample_output_dir)
        print(f"{sample_path.name} -> {sample_output_dir}")
        print(f"  flattened: {paths['flattened'].name}")
        print(f"  preview: {paths['preview'].name}")
        print(f"  details: {paths['details'].name}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
