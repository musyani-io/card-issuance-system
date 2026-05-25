# Phase 1: OCR Pipeline — Implementation Guide

## Overview
Phase 1 implements a 3-stage OpenCV + Tesseract pipeline to extract student registration numbers from UDSM ID cards. This document guides you through each stage of implementation and testing.

**Current Focus:** Phase 1.1 — Camera Capture & Lighting Validation  
**Target Completion:** >90% accuracy on first-attempt extraction  
**Estimated Duration:** 13.5 hours total

### SSH Mode & Headless Operation
This project runs in **SSH headless mode** (no attached display). The camera module (`ocr.py`) automatically detects SSH mode by checking if the `DISPLAY` environment variable is set:

```python
DISPLAY_AVAILABLE = os.getenv("DISPLAY") is not None
SSH_MODE = not DISPLAY_AVAILABLE
```

**Implication:** GUI-based tools (like `calibrate_roi.py`) cannot display windows over SSH. **Workaround:**
1. Capture frames and save them to `tests/fixtures/ocr_frames/`
2. Download frames to your Ubuntu PC
3. View and analyze frames in VS Code or image viewer
4. Manually enter calibration coordinates into `config.py` (or use SSH port forwarding with X11 if your Ubuntu has a display)

---

## Phase 1.1: Camera Capture & Lighting Validation (2.5 hrs)

### Objective
Verify that the Pi Camera is functional, properly positioned, and receiving adequate lighting to capture readable registration numbers.

### Prerequisites
- ✅ Pi Camera physically connected to CSI port (v2 or v3)
- ✅ Camera interface enabled in `raspi-config`
- ✅ `picamera` library installed for v2 (or `picamera2` for v3, or OpenCV fallback available)
- ✅ SSH access configured (for headless operation from Ubuntu PC)

### Tasks

#### Task 1.1.1 — Verify Camera is Functional

**Status:** ✅ IMPLEMENTED

Verifies the Pi Camera can capture frames at the target resolution (2560×1440 QHD).

**Run:**
```bash
cd kiosk_brain
python tests/test_camera.py
```

**What it does:**
1. Initializes the camera (picamera2 for v3, picamera for v2, or OpenCV fallback)
2. Captures 3 sequential frames with 500ms delay between captures
3. Saves frames to `tests/fixtures/ocr_frames/frame_YYYYMMDD_HHMMSS_mmm.jpg`
4. Reports frame dimensions, data type, and file sizes
5. Prints detailed diagnostics for troubleshooting

**Acceptance Criteria:**
- ✓ All 3 frames captured without errors
- ✓ Frames saved to `tests/fixtures/ocr_frames/` directory
- ✓ Frame dimensions are exactly 2560×1440 QHD
- ✓ Frame data type is uint8 (8-bit per channel)
- ✓ Each frame is ~450–500 KB (JPEG compressed)

**Expected Output:**
```
======================================================================
TASK 1.1.1 - CAMERA VERIFICATION TEST
======================================================================
Testing Pi Camera capture at (1280, 720)

[1/4] Initializing camera...
✓ Camera initialized successfully

[2/4] Capturing 3 test frames (500ms delay between captures)...
✓ Frame captured #1: shape=(720, 1280, 3), dtype=uint8
✓ Frame captured #2: shape=(720, 1280, 3), dtype=uint8
✓ Frame captured #3: shape=(720, 1280, 3), dtype=uint8
✓ Successfully captured 3 frames

[3/4] Analyzing captured frames...
   Frame 1:
      Shape (HxWxC): (720, 1280, 3)
      Data type: uint8
      Size: 0.35 MB
      ✓ Resolution correct: 1280x720
   ...

[4/4] Verifying saved frame files...
✓ Saved 3 frame files to tests/fixtures/ocr_frames/
   - frame_20260525_143022_456.jpg (342.1 KB)
   - frame_20260525_143022_961.jpg (338.5 KB)
   - frame_20260525_143022_1467.jpg (340.2 KB)

======================================================================
✅ SUCCESS: TASK 1.1.1 PASSED
======================================================================
```

**Troubleshooting:**

| Issue | Cause | Solution |
|-------|-------|----------|
| "Camera not ready for capture" | Camera not initialized | Check: `raspi-config` → Interface Options → Camera enabled? |
| ImportError: picamera2 | Library not installed | `pip install picamera2` (Pi only) |
| cv2.VideoCapture.read() failed | Camera not accessible | Check USB/CSI connection; restart Pi; try `fswebcam -r 1280x720` |
| Frames are blurry | Camera out of focus | Adjust camera lens (manual focus) or move camera closer/farther |
| Frames are very dark | Insufficient lighting | Natural light may not be adequate; consider adding LED (Task 1.1.3) |

---

#### Task 1.1.2 — Design Capture Workflow

**Status:** ✅ IMPLEMENTED (in CameraCapture class)

Defines how frames will be captured during the card ingestion process (staff batch loading).

**Configuration in `config.py`:**
```python
OCR_FRAME_RESOLUTION = (1280, 720)  # (width, height)
OCR_FRAME_RATE = 30  # fps - target frame rate
```

**Workflow Decisions Made:**
1. **Resolution:** 2560×1440 QHD (16:9 aspect ratio)
   - ✓ 4× more pixels for text clarity
   - ✓ Better OCR accuracy on small text
   - ✓ Capture time ~600ms per frame (acceptable for batch operation)
   
2. **Capture Mode:** Event-triggered (during staff batch loading)
   - ✓ Not continuous (saves CPU, power)
   - ✓ Triggered when card detected at Conveyor 1 scan station
   - ✓ Single capture per card (not multi-frame averaging yet)
   
3. **Frame Rate:** 30 fps target
   - ✓ Real-time processing on Pi 5
   - ✓ Sufficient for manual staff batch loading (~1 card every 2 seconds)

**Implementation Details:**
- CameraCapture class in `modules/ocr.py`
- Methods: `capture_frame()`, `capture_multiple_frames()`, `get_frame_info()`
- Supports both picamera2 (Pi) and OpenCV fallback (testing on desktop)
- Automatic frame storage to disk with timestamp filenames

---

#### Task 1.1.3 — Test Lighting Conditions

**Status:** ⏳ NEXT (Manual verification required)

Tests whether natural light is sufficient for OCR, or if an LED light source is needed.

**Procedure:**

1. **Inspect captured frames** (from Task 1.1.1)
   ```bash
   # View frames in ocr_frames/ directory
   file ocr_frames/*.jpg
   display ocr_frames/frame_*.jpg  # or open in any image viewer
   ```

2. **Check readability criteria:**
   - ✓ Can you easily read the registration number by eye?
   - ✓ Is the text sharp (not blurry)?
   - ✓ Is there glare or shadows obscuring the text?
   - ✓ Is the background uniform (no specular reflections)?

3. **Decision tree:**
   - **If text is clear and readable** → Natural light is adequate ✓
     - Proceed to Task 1.1.4
   - **If text is readable but dim** → Consider adding LED
     - Proceed with Task 1.1.4; add LED after calibration if accuracy < 90%
   - **If text is hard to read** → Add diffuse LED light source
     - Recommend: Warm white LED strip (5000–6500K) above scan station
     - Angle ~45° to minimize glare
     - Run test_camera.py again after adding light

**Acceptance Criteria:**
- ✓ Registration number is legible by human eye on at least 2 of 3 captured frames
- ✓ No severe glare or shadows on the registration number region
- ✓ Documented decision: "Natural light sufficient" or "Added LED light source"

---

#### Task 1.1.4 — Calibrate ROI Coordinates

**Status:** ✅ IMPLEMENTED (interactive tool ready)

Identifies the exact pixel coordinates of the registration number region on the ID card.

**Run:**
```bash
cd kiosk_brain
python tools/calibrate_roi.py
```

**What it does:**
1. Loads the latest frame from `ocr_frames/`
2. Displays the frame in a window
3. You click-and-drag to select the registration number region
4. Double-click to confirm
5. Coordinates are saved to `config.py` as `OCR_ROI_COORDINATES`

**Detailed Instructions:**

1. **Run the calibration tool:**
   ```bash
   python calibrate_roi.py
   ```

2. **When the frame window opens:**
   - Look for the registration number (left-center region)
   - Click at the **top-left corner** of the registration number
   - Drag to the **bottom-right corner**
   - Release the mouse button

3. **Verify the bounding box:**
   - A green rectangle appears showing your selection
   - Check that it tightly bounds the registration number
   - The instructions say "Double-click to confirm or click to restart"

4. **Confirm or restart:**
   - **To confirm:** Double-click anywhere on the frame
   - **To restart:** Single-click to select again

5. **Coordinates are saved:**
   ```python
   OCR_ROI_COORDINATES = (x1, y1, x2, y2)
   ```

**Acceptance Criteria:**
- ✓ ROI width is 100–200 pixels
- ✓ ROI tightly bounds the registration number area
- ✓ ROI coordinates saved to `config.py`
- ✓ Verified by running: `python show_roi.py`

**Example:**
```bash
$ python calibrate_roi.py

======================================================================
TASK 1.1.4 - ROI CALIBRATION
======================================================================

...

======================================================================
✅ ROI SELECTION COMPLETE
======================================================================

Selected coordinates: (150, 250, 400, 280)
ROI dimensions: 250px × 30px

✓ ROI width acceptable (100–200px)

Saving to config.py...
✓ config.py updated

Next steps:
  1. Verify ROI visually by running: python show_roi.py
  2. If satisfied, proceed to Task 1.2 (Image Preprocessing)
```

**Verification:**
```bash
$ python tools/show_roi.py

Loading frame: frame_20260525_143022_456.jpg
Displayed frame with ROI bounding box (green rectangle)
Press any key to close

✓ Visualization closed
```

---

## Phase 1.2: Image Preprocessing Pipeline (5 hrs)

### Overview
Prepares raw camera frames for OCR:
- Grayscale conversion
- Adaptive thresholding (binarization)
- Perspective correction (deskewing)
- ROI extraction
- Filtering & sharpening

**Status:** ⏳ NOT STARTED (blocked on Phase 1.1)

**Expected Implementation:**
```python
def preprocess_frame(frame: np.ndarray, roi_coordinates: Tuple[int, int, int, int]) -> Tuple[np.ndarray, np.ndarray]:
    """
    Returns:
        (preprocessed_frame, roi_crop)
    """
    # 1. Convert to grayscale
    # 2. Apply adaptive threshold
    # 3. Deskew (perspective correction)
    # 4. Crop to ROI
    # 5. Apply blur + sharpening
    # 6. Return both full preprocessed frame and ROI crop
```

---

## Phase 1.3: Tesseract OCR Integration (2 hrs)

### Overview
Extracts text from preprocessed frames using Tesseract.

**Status:** ⏳ NOT STARTED

**Expected Implementation:**
```python
def extract_registration_number(frame: np.ndarray, min_confidence: float = 0.85) -> Dict:
    """
    Returns:
        {
            "success": bool,
            "registration_number": str | None,
            "confidence": float,
            "error": str | None
        }
    """
```

---

## Phase 1.4: Validation & Reject Logic (1.5 hrs)

### Overview
Validates extracted text against UDSM registration number format.

**Status:** ✅ IMPLEMENTED (partially)

**Format Regex:**
```python
OCR_REGISTRATION_FORMAT_REGEX = r"^20\d{2}-04-\d{5}$"
# Matches: 2022-04-09050, 2023-04-12345
# Rejects: 2022-05-09050, 22-04-09050
```

---

## Phase 1.5: Accuracy Testing (2.5 hrs)

### Overview
Tests the complete pipeline against 20+ real UDSM ID cards to achieve ≥90% accuracy target.

**Status:** ⏳ NOT STARTED (blocked on Phases 1.2–1.4)

---

## File Structure

```
kiosk_brain/
├── modules/ocr.py                  # Core OCR module (CameraCapture class + functions)
├── config.py                        # OCR configuration constants
│
├── tests/                           # Test scripts & unit tests
│   ├── test_camera.py              # Task 1.1.1 verification script
│   ├── test_auth.py                # (existing) Auth testing
│   ├── test_ocr.py                 # OCR pipeline tests (1.2–1.5)
│   ├── test_spi.py                 # (existing) SPI testing
│   └── fixtures/                   # Test data & resources
│       └── ocr_frames/             # Captured test frames (generated)
│
├── tools/                          # Interactive CLI utilities
│   ├── calibrate_roi.py            # Task 1.1.4 ROI calibration tool
│   └── show_roi.py                 # ROI visualization script
│
└── PHASE1_README.md                # This file
```

---

## Running the Full Phase 1.1 Workflow

```bash
cd kiosk_brain

# Step 1: Verify camera
python tests/test_camera.py

# Step 2: Check captured frames visually
# - Open tests/fixtures/ocr_frames/*.jpg in image viewer
# - Verify registration number is readable
# - Note lighting conditions

# Step 3: Calibrate ROI
python tools/calibrate_roi.py

# Step 4: Verify ROI
python tools/show_roi.py

# Step 5: If satisfied
# - Proceed to Phase 1.2 (Image Preprocessing)
# - Or adjust camera angle/lighting and repeat Task 1.1.3
```

---

## Current Status

| Task | Status | Notes |
|------|--------|-------|
| 1.1.1 Verify camera | ✅ READY | `python test_camera.py` |
| 1.1.2 Design workflow | ✅ DONE | Resolution & frame rate configured |
| 1.1.3 Test lighting | ⏳ PENDING | Manual visual inspection required |
| 1.1.4 Calibrate ROI | ✅ READY | `python calibrate_roi.py` |
| 1.2 Preprocessing | ⏳ NOT STARTED | Blocked on 1.1 completion |
| 1.3 Tesseract OCR | ⏳ NOT STARTED | Blocked on 1.2 completion |
| 1.4 Validation | ⏳ PARTIAL | Regex implemented, decision logic stubbed |
| 1.5 Accuracy testing | ⏳ NOT STARTED | Blocked on 1.3 completion |

---

## Next Steps

1. **Immediately:** Run `python test_camera.py` to verify camera functionality
2. **After camera test:** Inspect frames in `ocr_frames/`; verify registration number is readable
3. **After visual inspection:** Run `python calibrate_roi.py` to calibrate ROI coordinates
4. **After calibration:** Proceed to Phase 1.2 (Image Preprocessing) ← Next milestone

---

## Troubleshooting

**Camera not detected:**
- Check physical CSI connection
- Run: `vcgencmd get_camera`
- Enable in: `sudo raspi-config` → Interface Options → Camera

**Frames not found error:**
- Run `python tests/test_camera.py` first to capture frames
- Frames are saved to `tests/fixtures/ocr_frames/`

**Frames are blurry:**
- Adjust Pi Camera lens (manual focus)
- Move camera closer/farther from card
- Verify card is held flat under camera

**Frames are dark:**
- Natural light may not be sufficient
- Add LED light source (warm white, 5000–6500K)
- Angle light at ~45° to minimize glare

**ROI calibration not saving:**
- Check file permissions: `ls -l config.py`
- Ensure `config.py` is writable: `chmod 644 config.py`

---

## Questions or Issues?

- Check the BUILD.md for overall project progress
- Review the OCR module documentation: `modules/ocr.py` docstring
- Test logs are printed to console; capture output with: `python test_camera.py 2>&1 | tee test_camera.log`
