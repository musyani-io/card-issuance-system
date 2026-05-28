# Computer Vision Module

## Overview

Image preprocessing and OCR detection module for the Automated Registration Card Issuance System. Handles image capture, preprocessing pipeline (grayscale conversion, resizing, ROI extraction), and OCR-based registration_number extraction for card identification and verification.

---

## Quick Start

### Installation

```bash
pip install -r requirements.txt
```

Ensure `opencv-python`, `pytesseract`, and `pillow` are installed in your environment.

---

## Module Structure

```bash
computer_vision/
├── core/              # Core CV functions (image_utils, ocr tools)
├── pipeline/          # Processing pipeline orchestration
├── config/            # Configuration files (camera, processing params)
├── tests/             # Manual and automated tests
├── docs/              # API reference, setup guides
└── __init__.py        # Module exports
```

---

## Implementation Status

**Overall Progress: 100%** - Ready for deployment

**Phase 1: Environment Setup** ✅ 100%

- ✅ Software installation complete
- ✅ Development environment configured
- ✅ Test data prepared

**Phase 2: Image Capture** ✅ 100%

- ✅ Camera configuration
- ✅ Input validation

**Phase 3: Image Preprocessing** ✅ 100%

- ✅ Basic preprocessing functions (grayscale, resize, ROI crop)
- ✅ Advanced preprocessing (blur, thresholding, morphology, CLAHE, denoise)
- ✅ Processing pipeline

**Phase 4: OCR Detection** ✅ 100%

- ✅ OCR detection with multiple strategies
- ✅ Field extraction & validation
- ✅ Edge case handling
- ✅ Testing suite

**Phase 5: Error Handling** ✅ 100%

- ✅ Custom exceptions
- ✅ Exception integration
- ✅ Graceful error responses

**Phase 6: Integration & Testing** ✅ 100%

- ✅ Public API (CardOCRPipeline)
- ✅ End-to-end testing
- ✅ Backend integration ready

---

## Core Components

### 1. Card Detection (`core/card_detector.py`)

- Detects card position in image
- Returns 4 corner points in order: [top-left, top-right, bottom-right, bottom-left]
- Uses Canny edge detection + contour filtering
- Filters by area, aspect ratio, corner count

**Key Functions:**

- `detect_card(image)` → corner points
- `preprocess_for_detection(image)` → edge image
- `find_card_contours(contours, image_shape)` → filtered contours
- `extract_corners(contour)` → ordered corner points

### 2. Perspective Correction (`core/perspective_corrector.py`)

- Applies perspective transform to flatten card
- Outputs standardized 880×550 pixel image
- Handles rotated/angled cards

**Key Functions:**

- `straighten_card(image, corners)` → flattened card image
- `order_points(pts)` → ordered corner array

### 3. Anchor-Based ROI Detection (`core/anchor_roi.py`)

- Finds "NAME" anchor label via OCR
- Derives relative ROI positions for other fields
- Extracts: name, registration_number, program, expiry_date

**Key Functions:**

- `find_anchor_box(image, anchor_texts, ...)` → anchor position
- `derive_rois_from_anchor(image, anchor_box, offsets)` → ROI positions dict

### 4. Image Preprocessing (`core/image_utils.py`)

- Grayscale conversion, resizing, cropping
- Denoise, contrast enhancement (CLAHE), binarization
- Full validation and error handling

**Key Functions:**

- `convert_to_grayscale(image)` → grayscale image
- `resize_image(image, max_width)` → resized image
- `enhance_contrast(image, ...)` → enhanced image
- `preprocess_for_ocr(image, config)` → binary image for OCR

### 5. Registration Number Validation (`core/student_id_validator.py`)

- Extracts registration_number via regex: `\d{4}-04-\d{5}`
- Validates format: 20XX-04-XXXXX
- Validates year range: 2015-2030
- OCR character corrections (O→0, I→1, L→1, S→5, B→8)
- Robust extraction from multiple OCR attempts

**Key Functions:**

- `extract_registration_number_robust(texts, pattern, ...)` → registration_number
- `validate_registration_number(...)` → bool

### 6. OCR Pipeline (`pipeline/ocr_pipeline.py`)

- Orchestrates entire processing flow end-to-end
- Handles: detection → perspective → anchor → ROI → OCR → validation
- Extracts all four fields with fallback strategies
- Comprehensive error handling

**Main Method:**

```python
pipeline = CardOCRPipeline(config)
result = pipeline.scan_card(image)
```

---

## Configuration Parameters

### `config/ocr_config.py`

**Card Specifications:**

```python
CARD_OUTPUT_SIZE = (880, 550)  # Standardized output: 10px/mm
CARD_PHYSICAL = {"width_mm": 88, "height_mm": 55}
```

**Anchor-Based ROI:**

```python
ANCHOR_OCR = {
    "anchor_texts": ["NAME"],
    "min_confidence": 50,
    "psm": 6,      # Tesseract PSM
    "oem": 3,      # Tesseract OEM
}

ANCHOR_ROI_OFFSETS = {
    "name": {"dx": -0.008, "dy": 0.064, "w": 0.648, "h": 0.073},
    "registration_number": {"dx": -0.010, "dy": 0.203, "w": 0.261, "h": 0.086},
    "program": {"dx": -0.013, "dy": 0.322, "w": 0.648, "h": 0.072},
    "expiry_date": {"dx": 0.166, "dy": 0.394, "w": 0.238, "h": 0.073},
}
```

**Registration Number Format:**

```python
STUDENT_ID_PATTERN = r"\d{4}-04-\d{5}"  # 20XX-04-XXXXX
VALID_YEAR_RANGE = (2015, 2030)
ID_TOTAL_LENGTH = 13
```

**Card Detection:**

```python
CARD_DETECTION = {
    "min_area": 10000,
    "max_area": 5000000,
    "aspect_ratio": 1.6,
    "canny_threshold1": 30,
    "canny_threshold2": 100,
}
```

**Preprocessing:**

```python
PREPROCESSING = {
    "enable_denoise": False,
    "enable_contrast": True,
    "enable_binarize": True,
    "clahe_clip_limit": 2.0,
    "binary_threshold_blocksize": 11,
}
```

---

## Usage Example

```python
import cv2
from computer_vision.pipeline.ocr_pipeline import CardOCRPipeline
from computer_vision.config.ocr_config import *

# Load image
image = cv2.imread("registration_card.jpg")

# Initialize pipeline with config
config = {
    "MAX_INPUT_WIDTH": 800,
    "ANCHOR_OCR": ANCHOR_OCR,
    "ANCHOR_ROI_OFFSETS": ANCHOR_ROI_OFFSETS,
    "STUDENT_ID_PATTERN": STUDENT_ID_PATTERN,
    "VALID_YEAR_RANGE": VALID_YEAR_RANGE,
    "ID_TOTAL_LENGTH": ID_TOTAL_LENGTH,
    "TESSERACT_CONFIG": TESSERACT_CONFIG,
    "TESSERACT_CONFIG_STRING": TESSERACT_CONFIG_STRING,
    "PREPROCESSING": PREPROCESSING,
    "DEBUG": DEBUG,
}

pipeline = CardOCRPipeline(config)

# Process card
result = pipeline.scan_card(image)

if result["success"]:
    print(f"Registration: {result['registration_number']}")
    print(f"Name: {result['name']}")
    print(f"Program: {result['program']}")
    print(f"Expiry: {result['expiry_date']}")
    print(f"Time: {result['processing_time_ms']:.2f}ms")
else:
    print(f"Error: {result['error']}")
```

---

## Result Format

```python
{
    "success": bool,
    "registration_number": str or None,
    "name": str or None,
    "program": str or None,
    "expiry_date": str or None,
    "confidence": float,
    "method": str,      # Processing stage
    "error": str or None,
    "processing_time_ms": float,
}
```

---

## Error Handling

**Custom Exceptions:**

- `CardNotFoundError` — No card detected in image
- `CardDetectionAmbiguousError` — Multiple cards detected
- `PerspectiveCorrectionError` — Perspective transform failed
- `OCRExtractionError` — OCR extraction failed
- `InvalidStudentIDError` — Registration number validation failed

All exceptions are caught gracefully; pipeline returns error result instead of crashing.

---

## Testing

```bash
# Run unit tests
python -m pytest tests/test_ocr_pipeline.py -v

# Run specific test
python -m pytest tests/test_ocr_pipeline.py::TestRegistrationNumberExtraction -v
```

**Test Coverage:**

- Card detection algorithms
- Perspective correction
- Registration number extraction & validation
- Image preprocessing pipeline
- Pipeline orchestration & error handling
- Result format validation

---

## Performance Notes

- **Input**: Any size image (auto-resized to max_width=800)
- **Output**: 880×550 pixel standardized card image
- **Speed**: ~500-1000ms per card (depends on image quality)
- **OCR Strategies**: 4 configurations (PSM 6/7 × original/inverted)
- **Preprocessing**: Contrast enhancement + adaptive binarization

---

## Known Limitations

1. **Gloss & Glare**: Shiny card surfaces may cause detection issues
2. **Blue Text**: Low contrast blue text on white background
3. **Watermark Interference**: Card watermarks may interfere with text detection
4. **Card Wear**: Worn edge wear may affect corner detection
5. **Angled Cards**: Very steep angles may fail perspective correction

---

## Backend Integration

### API Endpoint Example

```python
from fastapi import FastAPI, UploadFile, File
from computer_vision.pipeline.ocr_pipeline import CardOCRPipeline

app = FastAPI()
pipeline = CardOCRPipeline(config)

@app.post("/api/process-card")
async def process_card(file: UploadFile = File(...)):
    """Process registration card image."""
    image_data = await file.read()
    nparr = np.frombuffer(image_data, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

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
        return {
            "status": "success",
            "registration_number": result["registration_number"],
        }
    else:
        return {
            "status": "error",
            "message": result["error"],
        }
```

---

## References

- OpenCV documentation: https://docs.opencv.org
- Tesseract OCR: https://github.com/UB-Mannheim/tesseract/wiki
- PyTesseract: https://github.com/madmaze/pytesseract

---

## Version

**v1.0.0** - Initial release

- Complete card detection system
- Anchor-based ROI extraction
- Registration number validation
- All four fields extraction
- Comprehensive error handling
- Full test coverage
