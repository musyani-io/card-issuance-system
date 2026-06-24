"""
Live smoke test for the phone camera snapshot endpoint.

Run this only when your phone snapshot URL is reachable from the kiosk machine:

    cd kiosk_brain
    RUN_PHONE_CAMERA_LIVE_TEST=1 python -m unittest tests.test_phone_camera -v

The test fetches one image from the configured snapshot URL, verifies that it
decodes into an OpenCV image, and saves the captured frame under captures/
for manual inspection.
"""

from __future__ import annotations

import os
import sys
import unittest
from datetime import datetime
from pathlib import Path

import cv2
import urllib3
import requests

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import (
    PHONE_CAMERA_SNAPSHOT_URL,
    PHONE_CAMERA_TIMEOUT,
    PHONE_CAMERA_VERIFY_SSL,
)
from modules.phone_camera import PhoneCamera

if not PHONE_CAMERA_VERIFY_SSL:
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


@unittest.skipUnless(
    os.getenv("RUN_PHONE_CAMERA_LIVE_TEST") == "1",
    "set RUN_PHONE_CAMERA_LIVE_TEST=1 to run the live phone camera test",
)
class PhoneCameraLiveTest(unittest.TestCase):
    def test_capture_image(self):
        camera = PhoneCamera(
            PHONE_CAMERA_SNAPSHOT_URL,
            timeout=PHONE_CAMERA_TIMEOUT,
            verify_ssl=PHONE_CAMERA_VERIFY_SSL,
        )

        try:
            image = camera.capture_image()
        except RuntimeError as exc:
            self.fail(str(exc))
        except requests.RequestException as exc:
            self.fail(f"Request to {PHONE_CAMERA_SNAPSHOT_URL} failed: {exc}")

        self.assertIsNotNone(image)
        self.assertGreater(image.size, 0)
        self.assertEqual(len(image.shape), 3)
        self.assertEqual(image.shape[2], 3)

        output_dir = PROJECT_ROOT / "captures"
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = output_dir / f"phone_snapshot_{timestamp}.jpg"

        saved = cv2.imwrite(str(output_path), image)
        self.assertTrue(saved, "OpenCV failed to write the captured snapshot")
        self.assertTrue(output_path.exists(), "Snapshot file was not created")

        print(f"Captured snapshot saved to: {output_path}")
        print(f"Shape: {image.shape}, dtype: {image.dtype}")


if __name__ == "__main__":
    raise SystemExit(unittest.main())
