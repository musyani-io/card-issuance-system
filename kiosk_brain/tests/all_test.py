#!/usr/bin/env python3
"""Run all generate_task_*.py scripts from one command.

This script imports each generator module and calls its `main()` while
temporarily setting `sys.argv` so their argparse logic receives the
expected arguments. It does not change the behavior of the existing
generator modules.
"""

from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


GENERATORS = [
    "generate_task_1_2_1_detection_outputs.py",
    "generate_task_1_2_1_outputs.py",
    "generate_task_1_2_2_outputs.py",
    "generate_task_1_2_2_perspective_outputs.py",
    "generate_task_1_2_3_4_outputs.py",
    "generate_task_1_2_5_roi_outputs.py",
    "generate_task_1_3_ocr_outputs.py",
]


def load_and_run(script_path: Path, argv: list[str]) -> int:
    """Load a script from path and run its `main()` with given argv.

    Returns the integer exit code returned by the module `main()` or 1
    if an exception occurred.
    """
    name = script_path.stem
    spec = importlib.util.spec_from_file_location(name, str(script_path))
    if spec is None or spec.loader is None:
        print(f"Could not load {script_path}")
        return 1

    module = importlib.util.module_from_spec(spec)
    try:
        # execute module top-level (this defines main and helpers)
        spec.loader.exec_module(module)
    except Exception as exc:  # pragma: no cover - defensive
        print(f"Error importing {script_path}: {exc}")
        return 1

    # Preserve original argv for caller
    old_argv = sys.argv
    try:
        sys.argv = [str(script_path)] + argv
        if hasattr(module, "main"):
            return int(module.main() or 0)
        else:
            # Fallback: execute as script
            return 0
    except SystemExit as se:
        return int(getattr(se, "code", 0) or 0)
    except Exception as exc:  # pragma: no cover - defensive
        print(f"Error running {script_path}: {exc}")
        return 1
    finally:
        sys.argv = old_argv


def main() -> int:
    parser = argparse.ArgumentParser(description="Run all generate_task scripts")
    parser.add_argument(
        "--samples-dir",
        type=Path,
        default=SCRIPT_DIR / "fixtures" / "ocr_samples",
        help="Directory containing sample card images",
    )
    parser.add_argument(
        "--outputs-dir",
        type=Path,
        default=PROJECT_ROOT / "tests" / "outputs",
        help="Directory where outputs will be written",
    )
    parser.add_argument(
        "--whitelist",
        type=str,
        default=None,
        help="Whitelist string passed to OCR (only used by OCR script)",
    )
    parser.add_argument(
        "--roi",
        type=str,
        default=None,
        help="ROI string x,y,w,h (fractions) passed to ROI script",
    )
    parser.add_argument(
        "--only",
        type=str,
        default=None,
        help="Comma-separated list of generator basenames to run (defaults to all)",
    )

    args = parser.parse_args()

    samples_arg = f"--samples-dir={args.samples_dir}"
    outputs_arg = f"--outputs-dir={args.outputs_dir}"

    # determine which generators to run
    selected = set()
    if args.only:
        for name in args.only.split(","):
            selected.add(name.strip())

    exit_code = 0
    for gen in GENERATORS:
        base = Path(gen).stem
        if selected and base not in selected:
            print(f"Skipping {gen}")
            continue

        argv = [samples_arg, outputs_arg]
        # pass through optional args to the generators that accept them
        if args.whitelist:
            argv.append(f"--whitelist={args.whitelist}")
        if args.roi and "1_2_5" in gen:
            argv.append(f"--roi={args.roi}")

        script_path = SCRIPT_DIR / gen
        print(f"Running {gen} ...")
        code = load_and_run(script_path, argv)
        if code != 0:
            print(f"Generator {gen} exited with code {code}")
            exit_code = code or exit_code

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
