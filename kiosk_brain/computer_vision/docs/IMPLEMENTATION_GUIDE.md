# Build Computer Vision Module from Scratch

## Complete Implementation Guide

**Target Path:** `/home/musyani/Documents/Projects/card-issuance-system/kiosk_brain/computer_vision/`

**Project Goal:** Build a complete card detection and OCR extraction system for registration card processing that extracts: name, registration_number (format: `20XX-04-XXXXX`), program, and expiry_date.

---

## Architecture Overview

### System Flow

```bash
Input Image
    ↓
[1] Card Detection → Extract 4 corner points
    ↓
[2] Perspective Correction → Flatten to standardized 880×550 px
    ↓
[3] Anchor Detection → Find "NAME" label via OCR
    ↓
[4] Derive ROI Positions → Calculate field locations from anchor
    ↓
[5] Extract Fields → For each field: crop → preprocess → OCR
    ↓
[6] Validate → Check format patterns, year ranges
    ↓
API Endpoint + Database
```

### Technology Stack

- **OpenCV** (cv2): Image processing, edge detection, contours, perspective transform
- **Tesseract/pytesseract**: OCR text extraction
- **NumPy**: Array operations
- **Pillow**: Image I/O support

---

## Configuration Parameters (ALL CRITICAL)

### `config/ocr_config.py` - COMPLETE CONFIGURATION

```python
# Card Physical Specifications
CARD_PHYSICAL = {
    "width_mm": 88,
    "height_mm": 55,
    "standard": "CR80",
}

# Output size: 88mm / 55mm ≈ 1.6 aspect ratio, 10 pixels per mm
CARD_OUTPUT_SIZE = (880, 550)  # (width, height) in pixels

# Anchor-based ROI Detection Configuration
# Anchor label is "NAME" - fixed position reference point
ANCHOR_OCR = {
    "anchor_texts": ["NAME"],
    "min_confidence": 50,  # Tesseract confidence threshold (0-100)
    "psm": 6,  # Page Segmentation Mode: uniform block of text
    "oem": 3,  # OCR Engine Mode: Default (LSTM + Legacy combined)
    "char_whitelist": "ABCDEFGHIJKLMNOPQRSTUVWXYZ: ",
}

# ROI Offsets relative to anchor top-left corner
# Values are fractions of card width/height (0.0 to 1.0)
ANCHOR_ROI_OFFSETS = {
    "name": {
        "dx": -0.008,      # offset X: -0.8% of card width from anchor
        "dy": 0.064,       # offset Y: +6.4% of card height from anchor
        "w": 0.648,        # width: 64.8% of card width
        "h": 0.073,        # height: 7.3% of card height
    },
    "registration_number": {  # ← KEY NAME (NOT student_id)
        "dx": -0.010,
        "dy": 0.203,
        "w": 0.261,
        "h": 0.086,
    },
    "program": {
        "dx": -0.013,
        "dy": 0.322,
        "w": 0.648,
        "h": 0.072,
    },
    "expiry_date": {
        "dx": 0.166,
        "dy": 0.394,
        "w": 0.238,
        "h": 0.073,
    },
}

# Registration Number Validation (ADAPTED FOR NEW FORMAT)
STUDENT_ID_PATTERN = r"\d{4}-04-\d{5}"  # Format: 20XX-04-XXXXX (fixed April month)
VALID_YEAR_RANGE = (2015, 2030)
ID_TOTAL_LENGTH = 13  # 4 digits + dash + 2 digits + dash + 5 digits = "2024-04-12345"

# Card Detection Parameters (Canny edge detection + contour filtering)
CARD_DETECTION = {
    "min_area": 10000,           # Minimum contour area in pixels
    "max_area": 5000000,         # Maximum contour area in pixels
    "aspect_ratio": 1.6,         # Expected aspect ratio (88/55)
    "aspect_ratio_tolerance": 1.0,  # Allowed deviation (±100%)
    "canny_threshold1": 30,      # Lower threshold for Canny edge detection
    "canny_threshold2": 100,     # Upper threshold for Canny edge detection
}

# Tesseract OCR Configuration
TESSERACT_CONFIG = {
    "psm": 6,  # PSM 6: Assume uniform block of text
    "oem": 3,  # OEM 3: Default (LSTM + Legacy)
    "char_whitelist": "0123456789-",  # Only digits and hyphens for registration_number
}

# Build Tesseract config string (used in pipeline)
TESSERACT_CONFIG_STRING = (
    f"--psm {TESSERACT_CONFIG['psm']} "
    f"--oem {TESSERACT_CONFIG['oem']} "
    f"-c tessedit_char_whitelist={TESSERACT_CONFIG['char_whitelist']}"
)

# Image Preprocessing Pipeline Configuration
PREPROCESSING = {
    "enable_denoise": False,                 # FastNlMeansDenoising
    "enable_contrast": True,                 # CLAHE contrast enhancement
    "enable_binarize": True,                 # Adaptive thresholding
    "denoise_strength": 10,
    "denoise_template_window": 7,
    "denoise_search_window": 21,
    "clahe_clip_limit": 2.0,               # CLAHE clip limit
    "clahe_tile_grid_size": (8, 8),        # CLAHE tile size
    "gaussian_blur_kernel": (5, 5),        # Gaussian blur for detection
    "binary_threshold_blocksize": 11,      # Adaptive threshold block size (must be odd)
    "binary_threshold_c": 2,               # Adaptive threshold constant
}

# Performance & Retry Settings
MAX_INPUT_WIDTH = 800         # Resize input if wider than this
MAX_RETRIES = 3               # Maximum OCR retry attempts
PROCESSING_TIMEOUT_MS = 2000
CONFIDENCE_THRESHOLD = 0.7

# Debug Settings
DEBUG = {
    "save_intermediate_images": False,
    "debug_output_dir": "data/debug_outputs",
    "verbose_logging": False,
}
```

---

## Error Handling & Custom Exceptions

### `core/exceptions.py` - Exception Hierarchy

```python
class CardNotFoundError(Exception):
    """Raised when no card is detected in the image."""
    def __init__(self, message="No ID card detected in image."):
        self.message = message
        super().__init__(self.message)

class CardDetectionAmbiguousError(Exception):
    """Raised when multiple cards are detected (edge case)."""
    def __init__(self, message="Multiple cards detected in image."):
        self.message = message
        super().__init__(self.message)

class OCRExtractionError(Exception):
    """Raised when OCR fails to extract registration_number."""
    def __init__(self, message="Failed to extract registration_number from card."):
        self.message = message
        super().__init__(self.message)

class PerspectiveCorrectionError(Exception):
    """Raised when perspective correction fails."""
    def __init__(self, message="Failed to correct card perspective."):
        self.message = message
        super().__init__(self.message)

class InvalidStudentIDError(Exception):
    """Raised when extracted registration_number fails validation."""
    def __init__(self, message="Extracted registration_number is invalid."):
        self.message = message
        super().__init__(self.message)
```

---

## Core Algorithm Details

### 1. Card Detection Algorithm (`core/card_detector.py`)

**Purpose:** Detect the card in an image and return 4 corner points in order: [top-left, top-right, bottom-right, bottom-left].

**Algorithm Steps:**

1. **Preprocess for Detection:**
   - Convert BGR → Grayscale
   - Apply Gaussian blur: (7, 7) kernel
   - Canny edge detection: threshold1=30, threshold2=100
   - Dilate edges: kernel (5,5), iterations=2
   - Morphological close: kernel (5,5), iterations=1

2. **Find Contours:**
   - Use `cv2.findContours()` with `cv2.RETR_EXTERNAL` mode
   - Approximate: `cv2.CHAIN_APPROX_SIMPLE`

3. **Filter Contours (Card-like shapes):**
   - Area check: `min_area ≤ area ≤ max_area`
   - Polygon approximation: 4-12 vertices (use `cv2.approxPolyDP()` with epsilon=0.04\*perimeter)
   - Aspect ratio check: width/height ≈ 1.6 (tolerance ±1.0)
   - Reject if width or height is 0

4. **Extract & Order Corners:**
   - Use `cv2.minAreaRect()` to get bounding rectangle
   - Order points: top-left (min sum), top-right (min diff), bottom-right (max sum), bottom-left (max diff)
   - Return as np.ndarray shape (4, 2)

**Error Handling:**

- Raise `CardNotFoundError` if no valid contours found
- Raise `CardDetectionAmbiguousError` if multiple valid cards detected (use largest by area)
- Validate image is not None/empty before processing

---

### 2. Perspective Correction (`core/perspective_corrector.py`)

**Purpose:** Apply perspective transform to get a top-down, straightened view of the card.

**Algorithm Steps:**

1. **Order Points:**
   - Calculate point sums and differences
   - Assign: top-left = min(sum), top-right = min(diff), bottom-right = max(sum), bottom-left = max(diff)

2. **Perspective Transform:**
   - Source points: detected corners (4 points)
   - Destination points: standard rectangle (0,0), (880,0), (880,550), (0,550)
   - Use `cv2.getPerspectiveTransform()` to get transform matrix
   - Apply `cv2.warpPerspective()` to get straightened image

3. **Output:** Image of size (880, 550) in BGR format

---

### 3. Anchor-Based ROI Detection (`core/anchor_roi.py`)

**Purpose:** Find the "NAME" anchor label, then derive positions of other fields relative to anchor.

**Algorithm Steps:**

1. **Preprocess for Anchor OCR:**
   - Convert BGR → Grayscale
   - Gaussian blur: (3, 3)
   - Adaptive threshold: `cv2.adaptiveThreshold()` with Gaussian method, block=21, C=10

2. **Find Anchor Box:**
   - Run Tesseract with config (psm=6, oem=3, whitelist="ABCDEFGHIJKLMNOPQRSTUVWXYZ: ")
   - Extract text data with `pytesseract.image_to_data()`
   - Loop through detected text regions, normalize, filter by confidence
   - Match against anchor_texts list (["NAME"])
   - Keep highest confidence match
   - Return: (x, y, w, h) of anchor box

3. **Derive ROI Positions:**
   - Get anchor position and calculate ratios
   - For each field, apply offsets and clamp to [0, 1]
   - Return dict: `{ "name": {...}, "registration_number": {...}, ... }`

---

### 4. Registration Number Extraction & Validation (`core/student_id_validator.py`)

**Purpose:** Extract and validate registration_number from OCR text (format: `20XX-04-XXXXX`).

**OCR Correction Rules:**

```
'O' → '0', 'I' → '1', 'L' → '1', 'S' → '5', 'B' → '8'
```

**Validation Pipeline:**

1. **Extract candidate:** Use regex `\d{4}-04-\d{5}` to find matches
2. **Validate format:** Check total length = 13, pattern matches
3. **Validate year:** Extract first 4 digits, check within VALID_YEAR_RANGE (2015-2030)
4. **Retry strategy (robust extraction):**
   - Given list of OCR texts (multiple attempts)
   - For each text: attempt extraction, apply corrections if needed
   - Return most frequent valid ID, or None if none found

---

### 5. Image Preprocessing (`core/image_utils.py`)

**Purpose:** Chain image preprocessing operations for OCR readability.

**Pipeline (preprocess_for_ocr):**

1. Convert BGR → Grayscale (if needed)
2. **Optional Denoise** (enable_denoise=False by default)
   - `cv2.fastNlMeansDenoising()` with strength=10
3. **Optional Contrast Enhancement** (enable_contrast=True)
   - CLAHE: `cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))`
4. **Optional Binarization** (enable_binarize=True)
   - Adaptive threshold: `cv2.adaptiveThreshold()` with GAUSSIAN_C method

---

## OCR Pipeline Orchestration (`pipeline/ocr_pipeline.py`)

### `CardOCRPipeline` Class

**Purpose:** Orchestrate entire card scanning process end-to-end.

**Main Method: `scan_card(image) → Dict`**

**Flow (error handling at each step):**

1. **Input Validation:** Check image validity, convert grayscale if needed, resize if large
2. **Card Detection:** Call `detect_card()` → get corners
3. **Perspective Correction:** Call `straighten_card()` → get 880×550 card
4. **Anchor Detection:** Call `find_anchor_box()` → get anchor position
5. **Derive ROI Positions:** Call `derive_rois_from_anchor()` → get field positions
6. **Extract Registration Number:** Crop, preprocess, OCR, validate
7. **Extract Other Fields:** name, program, expiry_date (same process)
8. **Return Success Result:** Dict with all extracted fields + metadata

**Result Dictionary Format:**

```python
{
    "success": bool,
    "registration_number": str or None,
    "name": str or None,
    "program": str or None,
    "expiry_date": str or None,
    "confidence": float,
    "method": str,  # Processing stage
    "error": str or None,
    "processing_time_ms": float,
}
```

---

## Build Sequence (Dependencies)

**Phase 1: Foundation (Start here)**

1. Create all `__init__.py` files
2. Create `config/ocr_config.py`
3. Create `core/exceptions.py`

**Phase 2: Core Modules (Can build in parallel)** 4. Create `core/image_utils.py` 5. Create `core/card_detector.py` 6. Create `core/perspective_corrector.py` 7. Create `core/anchor_roi.py` 8. Create `core/student_id_validator.py`

**Phase 3: Orchestration** 9. Create `pipeline/ocr_pipeline.py`

**Phase 4: Testing & Documentation** 10. Create `tests/test_ocr_pipeline.py` 11. Create `tests/expected_results.json` 12. Create `README.md`

---

## Backend Integration Point

### Input Format (to pipeline)

```python
image = cv2.imread(image_path)  # BGR format, any size
result = pipeline.scan_card(image)
```

### Output Format (from pipeline)

```python
{
    "success": true/false,
    "registration_number": "2024-04-12345" or None,
    "name": "JOHN DOE" or None,
    "program": "COMPUTER SCIENCE" or None,
    "expiry_date": "2026-04-30" or None,
    "confidence": 0.0-1.0,
    "method": "stage_name",
    "error": "error message" or None,
    "processing_time_ms": float,
}
```

### Backend Handler (example)

```python
@app.post("/api/process-card")
def process_card(image_file):
    image = cv2.imread(image_file)
    result = pipeline.scan_card(image)

    if result["success"]:
        # Insert into database
        db.registrations.insert({
            "registration_number": result["registration_number"],
            "name": result["name"],
            "program": result["program"],
            "expiry_date": result["expiry_date"],
            "processed_at": datetime.now(),
        })
        return {"status": "success", "registration": result["registration_number"]}
    else:
        return {"status": "error", "message": result["error"]}, 400
```

---

## Critical Implementation Checkpoints

- [x] Config: All parameters defined exactly (STUDENT_ID_PATTERN = r"\d{4}-04-\d{5}")
- [x] Config: ANCHOR_ROI_OFFSETS has "registration_number" key
- [x] Exceptions: All 5 exception classes defined
- [x] Image Utils: All functions have full input validation
- [x] Card Detector: Uses config thresholds, handles multiple cards
- [x] Perspective: Returns exactly (880, 550) output
- [x] Anchor ROI: Clamps derived ratios to [0, 1]
- [x] Validator: Pattern matches 20XX-04-XXXXX format
- [x] Pipeline: Orchestrates all stages, catches exceptions
- [x] Pipeline: Extracts all 4 fields
- [x] Tests: Comprehensive test suite
- [x] Imports: All relative imports use correct paths

---

## Reference Implementation

Source files exist at:

- `/home/musyani/Documents/Projects/self-service-card-issuance/computer_vision/`

Use as blueprint for:

- Pattern replication
- Error handling structure
- Algorithm details
- Tesseract configuration strategies
- OCR retry logic
- Type hints and docstring style
