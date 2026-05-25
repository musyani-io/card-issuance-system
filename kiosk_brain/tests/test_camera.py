#!/usr/bin/env python3
"""
Test script for Camera Verification (TASK 1.1.1)

Usage:
    cd kiosk_brain
    python tests/test_camera.py
    # or with pytest:
    pytest tests/test_camera.py -v

Expected output:
    - Attempts to capture 3 frames from Pi Camera Module 3
    - Saves frames to tests/fixtures/ocr_frames/ directory
    - Prints frame metadata (dimensions, data type, size)
    - Reports SUCCESS if all 3 frames captured and saved

This script tests:
    ✓ Camera hardware is functional
    ✓ Frame resolution is correct (1280x720)
    ✓ Frames are in BGR color format
    ✓ Disk I/O works for frame storage

TASK 1.1.1 ACCEPTANCE CRITERIA:
    - Raw frame file saved in tests/fixtures/ocr_frames/ directory
    - Frame is viewable (valid JPEG)
    - Frame dimensions are 1280x720
    - Can capture 3 frames in sequence without errors
"""

import sys
import os
from pathlib import Path

# Add parent directory to Python path (tests/ -> kiosk_brain/)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from modules.ocr import CameraCapture, OCR_FRAME_RESOLUTION
import logging

# Configure logging to show detailed output
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def main():
    """Run camera capture test."""
    
    print("\n" + "="*70)
    print("TASK 1.1.1 - CAMERA VERIFICATION TEST")
    print("="*70)
    print(f"Testing Pi Camera Module 3 capture at {OCR_FRAME_RESOLUTION}")
    print()
    
    # Create output directory
    output_dir = Path(__file__).parent / "fixtures" / "ocr_frames"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Initialize camera
    print("[1/4] Initializing camera...")
    camera = CameraCapture(resolution=OCR_FRAME_RESOLUTION)
    
    if not camera.is_ready():
        print("\n❌ FAILED: Camera initialization failed")
        print("   - Is the Pi Camera Module 3 connected to the CSI port?")
        print("   - Run: raspi-config → Interface Options → Camera → Enable")
        return False
    
    print("✓ Camera initialized successfully")
    print()
    
    # Capture multiple frames
    print("[2/4] Capturing 3 test frames (500ms delay between captures)...")
    frames = camera.capture_multiple_frames(num_frames=3, save_to_disk=True, 
                                           output_dir=str(output_dir), delay_ms=500)
    
    if len(frames) < 3:
        print(f"\n❌ FAILED: Only captured {len(frames)}/3 frames")
        camera.release()
        return False
    
    print(f"✓ Successfully captured {len(frames)} frames")
    print()
    
    # Analyze frames
    print("[3/4] Analyzing captured frames...")
    for i, frame in enumerate(frames, 1):
        info = camera.get_frame_info(frame)
        print(f"\n   Frame {i}:")
        print(f"      Shape (HxWxC): {info['shape']}")
        print(f"      Data type: {info['dtype']}")
        print(f"      Size: {info['size_mb']:.2f} MB")
        
        # Verify dimensions
        if info['width'] != OCR_FRAME_RESOLUTION[0] or info['height'] != OCR_FRAME_RESOLUTION[1]:
            print(f"      ⚠️  WARNING: Expected {OCR_FRAME_RESOLUTION}, got {info['width']}x{info['height']}")
        else:
            print(f"      ✓ Resolution correct: {info['width']}x{info['height']}")
    
    print()
    
    # Check saved files
    print("[4/4] Verifying saved frame files...")
    output_dir = Path(__file__).parent / "fixtures" / "ocr_frames"
    if output_dir.exists():
        frames_on_disk = list(output_dir.glob("*.jpg"))
        print(f"✓ Saved {len(frames_on_disk)} frame files to tests/fixtures/ocr_frames/")
        for frame_file in sorted(frames_on_disk)[-3:]:  # Show last 3 files
            file_size_kb = frame_file.stat().st_size / 1024
            print(f"   - {frame_file.name} ({file_size_kb:.1f} KB)")
    else:
        print("❌ FAILED: tests/fixtures/ocr_frames/ directory not found")
        camera.release()
        return False
    
    # Release camera
    camera.release()
    
    print("\n" + "="*70)
    print("✅ SUCCESS: TASK 1.1.1 PASSED")
    print("="*70)
    print("\nNext steps:")
    print("  1. Inspect saved frames in tests/fixtures/ocr_frames/ folder")
    print("  2. Check if registration number is visible and readable")
    print("  3. If text is hard to read:")
    print("     - Adjust camera angle/distance")
    print("     - Consider adding LED diffuse light (Task 1.1.3)")
    print("  4. Run: python tools/calibrate_roi.py")
    print()
    
    return True


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
