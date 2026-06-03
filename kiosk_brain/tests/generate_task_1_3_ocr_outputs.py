#!/usr/bin/env python3
"""Run Tesseract OCR on ROI outputs produced by save_roi_preview().

This script will re-run ROI extraction (to ensure outputs exist) and then run
Tesseract with two methods (psm 7 and psm 8) and save results to the sample
output folder as `ocr_psm7.txt`, `ocr_psm7_conf.txt`, etc.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.card_detector import save_roi_preview
from modules.ocr import perform_ocr


def iter_sample_images(samples_dir: Path) -> list[Path]:
    allowed_suffixes = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}
    return sorted(
        path for path in samples_dir.iterdir() if path.is_file() and path.suffix.lower() in allowed_suffixes
    )


def build_output_root(project_root: Path) -> Path:
    return project_root / "tests" / "outputs"


def run_for_method(sample_path: Path, outputs_dir: Path, psm: int, whitelist: str | None):
    sample_out = outputs_dir / sample_path.stem
    sample_out.mkdir(parents=True, exist_ok=True)
    # Ensure ROI artifacts exist
    save_roi_preview(sample_path, sample_out)
    roi_thresh = sample_out / "roi_threshold.jpg"
    roi_preocr = sample_out / "roi_preocr.jpg"

    targets = []
    if roi_thresh.exists():
        targets.append((roi_thresh, "threshold"))
    if roi_preocr.exists():
        targets.append((roi_preocr, "preocr"))

    import re
    pattern = re.compile(r"^20\d{2}-04-\d{5}$")

    for img_path, tag in targets:
        from PIL import Image
        import numpy as np

        im = Image.open(img_path)
        # convert to grayscale numpy array expected by perform_ocr
        im_np = np.array(im.convert("L"))
        try:
            res = perform_ocr(im_np, psm=psm, whitelist=whitelist)
        except Exception as exc:
            (sample_out / f"ocr_psm{psm}_{tag}_error.txt").write_text(str(exc), encoding="utf-8")
            continue

        text = res.get("text", "")
        conf = res.get("mean_confidence")

        (sample_out / f"ocr_psm{psm}_{tag}.txt").write_text(text, encoding="utf-8")
        (sample_out / f"ocr_psm{psm}_{tag}_conf.txt").write_text(str(conf), encoding="utf-8")

        # Regex validation for pattern 20XX-04-XXXXX (digits + hyphens)
        matched = bool(pattern.search(text))
        (sample_out / f"ocr_psm{psm}_{tag}_match.txt").write_text(str(matched), encoding="utf-8")
        if matched:
            (sample_out / f"ocr_psm{psm}_{tag}_match_text.txt").write_text(pattern.search(text).group(0), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Tesseract OCR on ROI outputs")
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
    parser.add_argument(
        "--whitelist",
        type=str,
        default=None,
        help="Character whitelist to pass to Tesseract (e.g. 0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ)",
    )
    args = parser.parse_args()

    samples = iter_sample_images(args.samples_dir)
    if not samples:
        print("No sample images found")
        return 1

    print(f"Found {len(samples)} sample images")
    for s in samples:
        print(f"Processing {s.name}")
        run_for_method(s, args.outputs_dir, psm=7, whitelist=args.whitelist)
        run_for_method(s, args.outputs_dir, psm=8, whitelist=args.whitelist)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
