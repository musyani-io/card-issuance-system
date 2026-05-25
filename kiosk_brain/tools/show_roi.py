#!/usr/bin/env python3
"""
ROI Visualization Script

Usage:
    cd kiosk_brain
    python tools/show_roi.py

Displays the captured frame with the calibrated ROI bounding box overlaid.
Useful for verifying that the ROI coordinates are correct before moving to Task 1.2.
"""

import sys
import os
from pathlib import Path

# Add parent directory to Python path (tools/ -> kiosk_brain/)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import cv2
import config

def main():
    """Display frame with ROI overlay."""
    
    print("\n" + "="*70)
    print("ROI VISUALIZATION")
    print("="*70)
    print()
    
    # Check ROI configuration
    if config.OCR_ROI_COORDINATES is None:
        print("❌ ROI not yet calibrated")
        print("   Run: python calibrate_roi.py")
        return False
    
    print(f"Configured ROI: {config.OCR_ROI_COORDINATES}")
    print()
    
    # Find latest frame
    frame_dir = Path(__file__).parent.parent / "tests" / "fixtures" / "ocr_frames"
    if not frame_dir.exists() or not list(frame_dir.glob("*.jpg")):
        print("❌ No frames found in tests/fixtures/ocr_frames/")
        return False
    
    latest_frame_path = sorted(frame_dir.glob("*.jpg"))[-1]
    print(f"Loading frame: {latest_frame_path.name}")
    
    # Load and process frame
    frame = cv2.imread(str(latest_frame_path))
    if frame is None:
        print("❌ Failed to load frame")
        return False
    
    # Draw ROI on frame
    x1, y1, x2, y2 = config.OCR_ROI_COORDINATES
    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
    cv2.putText(frame, "ROI", (x1 + 5, y1 + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    
    # Display
    cv2.namedWindow("ROI Visualization", cv2.WINDOW_NORMAL)
    cv2.imshow("ROI Visualization", frame)
    
    print()
    print("Displayed frame with ROI bounding box (green rectangle)")
    print("Press any key to close")
    print()
    
    cv2.waitKey(0)
    cv2.destroyAllWindows()
    
    print("✓ Visualization closed")
    return True


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
