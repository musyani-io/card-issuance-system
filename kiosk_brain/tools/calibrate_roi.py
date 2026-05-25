#!/usr/bin/env python3
"""
ROI Calibration Script (TASK 1.1.4)

Usage:
    cd kiosk_brain
    python tools/calibrate_roi.py

This script helps you identify the pixel coordinates of the registration number region
on your ID card frames. It displays a captured frame and lets you interactively select
the bounding box for the registration number.

TASK 1.1.4 ACCEPTANCE CRITERIA:
    - ROI crop is 100–200 px wide
    - Contains only registration number area
    - Pixel coordinates documented in config.py as OCR_ROI_COORDINATES
    
Instructions:
    1. Script loads latest frame from tests/fixtures/ocr_frames/ directory
    2. Click and drag to select registration number region
    3. Double-click to finish selection
    4. Coordinates are printed and saved to config.py
"""

import sys
import os
from pathlib import Path

# Add parent directory to Python path (tools/ -> kiosk_brain/)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import cv2
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global state for mouse interaction
roi_points = []
roi_selecting = False
roi_final = None
display_frame = None


def mouse_callback(event, x, y, flags, param):
    """Mouse callback for ROI selection."""
    global roi_points, roi_selecting, roi_final, display_frame
    
    if event == cv2.EVENT_LBUTTONDOWN:
        roi_points = [(x, y)]
        roi_selecting = True
        logger.info(f"ROI selection started at ({x}, {y})")
    
    elif event == cv2.EVENT_MOUSEMOVE and roi_selecting:
        # Draw rectangle preview
        temp_frame = display_frame.copy()
        if len(roi_points) > 0:
            cv2.rectangle(temp_frame, roi_points[0], (x, y), (0, 255, 0), 2)
        cv2.imshow("ROI Calibration", temp_frame)
    
    elif event == cv2.EVENT_LBUTTONUP:
        roi_points.append((x, y))
        roi_selecting = False
        logger.info(f"ROI selection ended at ({x}, {y})")
        
        if len(roi_points) == 2:
            x1, y1 = roi_points[0]
            x2, y2 = roi_points[1]
            # Ensure correct order
            x1, x2 = min(x1, x2), max(x1, x2)
            y1, y2 = min(y1, y2), max(y1, y2)
            roi_final = (x1, y1, x2, y2)
            
            # Draw final rectangle
            temp_frame = display_frame.copy()
            cv2.rectangle(temp_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(temp_frame, f"ROI: ({x1}, {y1}, {x2}, {y2})", 
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(temp_frame, "Double-click to confirm or click to restart", 
                       (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
            cv2.imshow("ROI Calibration", temp_frame)
    
    elif event == cv2.EVENT_LBUTTONDBLCLK:
        if roi_final is not None:
            logger.info(f"ROI selection confirmed: {roi_final}")
            # Trigger window close by returning a key
        else:
            roi_points = []
            logger.info("Double-click detected but no ROI yet. Restart selection.")


def main():
    """Run ROI calibration."""
    global display_frame
    
    print("\n" + "="*70)
    print("TASK 1.1.4 - ROI CALIBRATION")
    print("="*70)
    print()
    print("This tool helps identify the pixel coordinates of the registration number")
    print("region on your ID cards.")
    print()
    print("Instructions:")
    print("  1. A captured frame will be displayed")
    print("  2. Click and drag to select the registration number region")
    print("  3. Double-click to confirm your selection")
    print("  4. Coordinates will be saved to config.py")
    print()
    
    # Find latest frame
    frame_dir = Path(__file__).parent.parent / "tests" / "fixtures" / "ocr_frames"
    if not frame_dir.exists() or not list(frame_dir.glob("*.jpg")):
        print("❌ FAILED: No frames found in tests/fixtures/ocr_frames/")
        print("   Run 'python tests/test_camera.py' first to capture frames")
        return False
    
    latest_frame_path = sorted(frame_dir.glob("*.jpg"))[-1]
    print(f"[1/3] Loading frame: {latest_frame_path.name}")
    
    # Load frame
    frame = cv2.imread(str(latest_frame_path))
    if frame is None:
        print("❌ FAILED: Could not load frame")
        return False
    
    display_frame = frame.copy()
    print(f"✓ Frame loaded: {frame.shape}")
    print()
    
    # Create window
    print("[2/3] Opening frame viewer...")
    cv2.namedWindow("ROI Calibration", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("ROI Calibration", 1280, 720)
    cv2.setMouseCallback("ROI Calibration", mouse_callback)
    
    # Display instructions overlay
    temp_frame = display_frame.copy()
    cv2.putText(temp_frame, "Click and drag to select registration number region", 
               (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 255, 0), 2)
    cv2.putText(temp_frame, "Double-click to confirm", 
               (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 255, 0), 2)
    cv2.imshow("ROI Calibration", temp_frame)
    print("✓ Viewer ready - select ROI on the displayed frame")
    print()
    
    # Wait for user interaction
    print("[3/3] Waiting for your ROI selection...")
    print("   (Press ESC to cancel)")
    print()
    
    while True:
        key = cv2.waitKey(1) & 0xFF
        if key == 27:  # ESC
            print("❌ Cancelled by user")
            cv2.destroyAllWindows()
            return False
        
        if roi_final is not None:
            break
    
    cv2.destroyAllWindows()
    
    # Validate ROI
    x1, y1, x2, y2 = roi_final
    width = x2 - x1
    height = y2 - y1
    
    print()
    print("="*70)
    print("✅ ROI SELECTION COMPLETE")
    print("="*70)
    print()
    print(f"Selected coordinates: ({x1}, {y1}, {x2}, {y2})")
    print(f"ROI dimensions: {width}px × {height}px")
    print()
    
    # Validate dimensions
    if width < 100:
        print("⚠️  WARNING: ROI width < 100px (may be too small)")
    elif width > 200:
        print("⚠️  WARNING: ROI width > 200px (may include extra regions)")
    else:
        print("✓ ROI width acceptable (100–200px)")
    
    print()
    print("Saving to config.py...")
    update_config(roi_final)
    print("✓ config.py updated")
    print()
    print("Next steps:")
    print("  1. Verify ROI visually by running: python show_roi.py")
    print("  2. If satisfied, proceed to Task 1.2 (Image Preprocessing)")
    print("  3. If not satisfied, run this script again to re-calibrate")
    print()
    
    return True


def update_config(roi_coordinates):
    """Update config.py with new ROI coordinates."""
    config_path = Path("config.py")
    
    if not config_path.exists():
        logger.error("config.py not found")
        return
    
    with open(config_path, 'r') as f:
        content = f.read()
    
    # Replace OCR_ROI_COORDINATES
    old_line = "OCR_ROI_COORDINATES = None"
    new_line = f"OCR_ROI_COORDINATES = {roi_coordinates}"
    
    content = content.replace(old_line, new_line)
    
    with open(config_path, 'w') as f:
        f.write(content)


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
