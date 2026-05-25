# Phase 1 OCR Pipeline — Implementation Plan

> **Status**: Camera capture verified ✅ (Task 1.1.1 complete)  
> **Next**: Phone image capture + Tasks 1.2–1.5 (Image preprocessing → OCR → Validation → Testing)  
> **Timeline**: ~13 hrs remaining work  
> **Date Created**: 25 May 2026

---

## 🎯 Overall Objective

Convert phone-captured ID card images into extracted registration numbers with >90% accuracy using:
1. OpenCV preprocessing (grayscale → threshold → deskew → ROI crop → sharpen)
2. Tesseract OCR (single-line mode with alphanumeric whitelist)
3. Regex validation against UDSM registration format
4. Confidence scoring and threshold tuning

---

## 📋 Pre-Implementation Checklist (Before You Start)

- [ ] Capture 5–10 phone images of ID card and save locally
- [ ] Create directory: `kiosk_brain/tests/fixtures/ocr_samples/`
- [ ] Upload phone images to that directory
- [ ] Verify images are in JPEG or PNG format
- [ ] Confirm registration numbers are clearly visible in each image

**Expected outcome**: `tests/fixtures/ocr_samples/card_001.jpg` through `card_010.jpg` (or equivalent)

---

## 📸 Phone Image Capture Guidelines

### Camera Setup
- **Phone**: Any smartphone with 8MP+ camera (standard phone sufficient)
- **Lighting**: Diffuse white light (window light ideal, avoid harsh shadows)
- **Surface**: Flat table or desk
- **Distance**: ~30–40cm from card to camera lens
- **Angle**: Perpendicular to card (straight-on, not tilted)

### Capture Technique
1. Place ID card flat on surface, parallel to ground
2. Position phone directly above at ~30–40cm distance
3. Ensure entire card fills frame uniformly (60–70% of frame)
4. Take 5–10 photos at slightly different angles/distances
5. Avoid glare on card surface (adjust lighting if needed)

### Expected Image Properties
- **Resolution**: 3000×4000+ pixels (standard smartphone photo)
- **Format**: JPEG (recommended) or PNG
- **File size**: 1–5 MB per image
- **Content**: Full card with registration number clearly visible

### File Organization
```bash
kiosk_brain/tests/fixtures/ocr_samples/
├── card_001.jpg
├── card_002.jpg
├── card_003.jpg
├── card_004.jpg
├── card_005.jpg
└── (up to card_010.jpg if you have more)
```

---

## 🚀 Implementation Workflow (After Images Captured)

### Phase 1: Organize Images (5 min)
```bash
cd kiosk_brain/tests/fixtures

# If ocr_samples directory doesn't exist:
mkdir -p ocr_samples

# Copy or move your phone images here
# Example (if stored on desktop):
# cp ~/Desktop/card_*.jpg ./ocr_samples/

# Verify images are present:
ls -lh ocr_samples/
```

**Expected output**: 5–10 `.jpg` files, each 1–5 MB

---

### Phase 2: Task 1.2 — OpenCV Preprocessing Pipeline (2.5–3 hrs)

**Goal**: Create a preprocessing function that cleans phone images before OCR

**Implementation steps**:

#### 1.2.1 Grayscale Conversion (30 min)
**File**: `kiosk_brain/modules/ocr.py`

Add a new function `preprocess_image(image_path)`:
```python
def preprocess_image(image_path):
    """
    Read image and convert to grayscale.
    
    Args:
        image_path (str): Path to image file (JPEG, PNG, etc.)
    
    Returns:
        np.ndarray: Grayscale image (H, W) uint8
    
    Raises:
        FileNotFoundError: If image file doesn't exist
        ValueError: If image cannot be loaded
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found: {image_path}")
    
    # Read image in color
    image = cv2.imread(image_path)
    if image is None:
        raise ValueError(f"Failed to load image: {image_path}")
    
    # Convert BGR (OpenCV default) to RGB
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    
    # Convert to grayscale
    gray = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2GRAY)
    
    return gray
```

**Test it**:
```python
# In Python REPL or test script:
from modules.ocr import preprocess_image
gray = preprocess_image('tests/fixtures/ocr_samples/card_001.jpg')
print(f"Grayscale shape: {gray.shape}, dtype: {gray.dtype}")
```

---

#### 1.2.2 Bilateral Filtering (30 min)
**Purpose**: Reduce noise while preserving card edges

Add to `preprocess_image()`:
```python
def preprocess_image(image_path):
    """...[existing docstring]"""
    # ... [grayscale conversion code from 1.2.1]
    
    # Apply bilateral filter for noise reduction
    # From config.py: OCR_BILATERAL_FILTER_D, OCR_BILATERAL_FILTER_SIGMA
    d = config.OCR_BILATERAL_FILTER_D  # 11
    sigma_color = config.OCR_BILATERAL_FILTER_SIGMA  # 75
    sigma_space = config.OCR_BILATERAL_FILTER_SIGMA  # 75
    
    filtered = cv2.bilateralFilter(gray, d, sigma_color, sigma_space)
    return filtered
```

**Verify in config.py**:
```python
# kiosk_brain/config.py should have:
OCR_BILATERAL_FILTER_D = 11
OCR_BILATERAL_FILTER_SIGMA = 75
```
✅ Already present (check lines 90–100 of config.py)

**Test it**:
```python
filtered = preprocess_image('tests/fixtures/ocr_samples/card_001.jpg')
print(f"Filtered shape: {filtered.shape}")
```

---

#### 1.2.3 Adaptive Thresholding (45 min)
**Purpose**: Binarize image (black/white only) to handle uneven lighting

Add to `preprocess_image()`:
```python
def preprocess_image(image_path):
    """...[existing docstring]"""
    # ... [grayscale → bilateral filter code]
    
    # Apply adaptive thresholding
    # From config.py: OCR_ADAPTIVE_THRESHOLD_BLOCKSIZE, OCR_ADAPTIVE_THRESHOLD_C
    block_size = config.OCR_ADAPTIVE_THRESHOLD_BLOCKSIZE  # 11
    c_value = config.OCR_ADAPTIVE_THRESHOLD_C  # 5
    
    thresholded = cv2.adaptiveThreshold(
        filtered,
        maxValue=255,
        adaptiveMethod=cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        thresholdType=cv2.THRESH_BINARY,
        blockSize=block_size,
        C=c_value
    )
    
    return thresholded
```

**Verify in config.py**:
```python
# kiosk_brain/config.py should have:
OCR_ADAPTIVE_THRESHOLD_BLOCKSIZE = 11
OCR_ADAPTIVE_THRESHOLD_C = 5
```
✅ Already present (check lines 100–110 of config.py)

---

#### 1.2.4 Deskewing (1 hr)
**Purpose**: Detect card tilt angle and rotate back to straight

Add a helper function:
```python
def deskew_image(image):
    """
    Detect card edge angle using Hough lines and rotate to straighten.
    
    Args:
        image (np.ndarray): Binary image (output from adaptive threshold)
    
    Returns:
        np.ndarray: Deskewed binary image
    """
    # Detect edges with Canny
    edges = cv2.Canny(
        image,
        threshold1=config.OCR_CANNY_THRESHOLD1,  # 100
        threshold2=config.OCR_CANNY_THRESHOLD2   # 200
    )
    
    # Detect lines using Hough transform
    lines = cv2.HoughLines(edges, rho=1, theta=np.pi/180, threshold=100)
    
    if lines is None or len(lines) == 0:
        # No clear lines detected, return image as-is
        return image
    
    # Extract angle from first detected line
    rho, theta = lines[0][0]
    angle = (theta * 180 / np.pi) - 90  # Convert to degrees
    
    # Adjust angle to [-45, 45] range
    if angle > 45:
        angle -= 90
    if angle < -45:
        angle += 90
    
    # Rotate image
    h, w = image.shape[:2]
    center = (w // 2, h // 2)
    rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
    deskewed = cv2.warpAffine(
        image, rotation_matrix, (w, h),
        borderMode=cv2.BORDER_REPLICATE
    )
    
    return deskewed
```

**Update preprocess_image() to call deskew**:
```python
def preprocess_image(image_path):
    """...[existing docstring]"""
    # ... [grayscale → bilateral → threshold code]
    
    # Deskew the thresholded image
    deskewed = deskew_image(thresholded)
    
    return deskewed
```

**Verify in config.py**:
```python
# kiosk_brain/config.py should have:
OCR_CANNY_THRESHOLD1 = 100
OCR_CANNY_THRESHOLD2 = 200
```
✅ Already present (check lines 110–120 of config.py)

---

#### 1.2.5 ROI Crop (30 min)
**Purpose**: Extract just the registration number region

First, **calibrate ROI coordinates**:
```python
# In tests/test_preprocess.py or REPL:
import cv2
from modules.ocr import preprocess_image

img = preprocess_image('tests/fixtures/ocr_samples/card_001.jpg')
h, w = img.shape

# Display image and manually find registration number region
# Example: registration number typically in top-right of card
# On a standard ID card: ~x=300, y=50, width=200, height=50

# For now, use placeholder ROI (you'll calibrate after visual inspection)
ROI_X = 300      # pixels from left
ROI_Y = 50       # pixels from top
ROI_WIDTH = 200  # pixels wide
ROI_HEIGHT = 50  # pixels tall
```

**Update config.py**:
```python
# kiosk_brain/config.py
OCR_ROI_COORDINATES = (300, 50, 200, 50)  # (x, y, width, height)
```

**Add ROI crop to preprocess_image()**:
```python
def preprocess_image(image_path, use_roi=True):
    """...[existing docstring]"""
    # ... [grayscale → bilateral → threshold → deskew code]
    
    if use_roi:
        # Extract Region of Interest (registration number area)
        x, y, w, h = config.OCR_ROI_COORDINATES
        roi = deskewed[y:y+h, x:x+w]
        return roi
    
    return deskewed
```

---

#### 1.2.6 Sharpening (30 min)
**Purpose**: Enhance character edges before OCR

Add a helper:
```python
def sharpen_image(image):
    """
    Apply unsharp mask sharpening to enhance character edges.
    
    Args:
        image (np.ndarray): Input image
    
    Returns:
        np.ndarray: Sharpened image
    """
    # Define sharpening kernel
    kernel = np.array([
        [0, -1, 0],
        [-1, 5, -1],
        [0, -1, 0]
    ], dtype=np.float32)
    
    # Apply kernel
    sharpened = cv2.filter2D(image, -1, kernel)
    
    return sharpened
```

**Update preprocess_image()**:
```python
def preprocess_image(image_path, use_roi=True):
    """...[existing docstring]"""
    # ... [all previous steps]
    
    if use_roi:
        roi = deskewed[y:y+h, x:x+w]
        # Sharpen the ROI
        return sharpen_image(roi)
    
    return deskewed
```

---

### Phase 3: Task 1.3 — Tesseract OCR Integration (1–1.5 hrs)

**Goal**: Extract registration number text from preprocessed image

#### 1.3.1 Install Tesseract (already done ✅)
```bash
# Check Tesseract is installed:
tesseract --version
# Should output: tesseract 5.x.x...

# Verify pytesseract Python bindings:
python3 -c "import pytesseract; print(pytesseract.pytesseract.pytesseract_cmd)"
# Should return the path or None (if in PATH)
```

#### 1.3.2 Add OCR extraction function (45 min)
**File**: `kiosk_brain/modules/ocr.py`

```python
def extract_registration_number(preprocessed_image):
    """
    Run Tesseract OCR on preprocessed image.
    
    Args:
        preprocessed_image (np.ndarray): Binary image from preprocess_image()
    
    Returns:
        dict: {
            'text': str (extracted text),
            'confidence': float (0.0–1.0),
            'details': dict (raw Tesseract output data)
        }
    """
    import pytesseract
    
    # Configure Tesseract options
    config = pytesseract.pytesseract
    
    # --psm 7 = single line of text mode
    # --oem 3 = use both legacy and LSTM OCR engine
    custom_config = r'--psm 7 --oem 3'
    
    # Apply character whitelist (digits, hyphen only)
    whitelist = config.OCR_TESSERACT_CHAR_WHITELIST  # "0123456789-"
    custom_config += f' -c tessedit_char_whitelist={whitelist}'
    
    # Run OCR
    try:
        # Get text with confidence scores
        data = pytesseract.image_to_data(
            preprocessed_image,
            config=custom_config,
            output_type=pytesseract.Output.DICT
        )
        
        # Extract text
        text = " ".join([w for w in data['text'] if w.strip()])
        
        # Calculate confidence (average of all word confidences)
        confidences = [int(c) for c in data['confidence'] if int(c) > 0]
        avg_confidence = (sum(confidences) / len(confidences)) / 100.0 if confidences else 0.0
        
        return {
            'text': text.strip(),
            'confidence': avg_confidence,
            'details': data
        }
    
    except pytesseract.TesseractNotFoundError:
        return {
            'text': '',
            'confidence': 0.0,
            'error': 'Tesseract not installed'
        }
```

**Verify in config.py**:
```python
# kiosk_brain/config.py should have:
OCR_TESSERACT_PSM = 7  # Single line
OCR_TESSERACT_CHAR_WHITELIST = "0123456789-"
OCR_TESSERACT_MIN_CONFIDENCE = 0.85
```
✅ Already present (check lines 125–140 of config.py)

---

### Phase 4: Task 1.4 — Regex Validation (45 min)

**Goal**: Validate extracted text matches registration number format

#### 1.4.1 Add regex validation function
**File**: `kiosk_brain/modules/ocr.py`

```python
def validate_registration_format(text):
    """
    Check if extracted text matches UDSM registration number format.
    
    Format: YYYY-MM-XXXXX
    Example: 2024-04-12345 (year-month-sequence)
    
    Args:
        text (str): Extracted registration number
    
    Returns:
        dict: {
            'is_valid': bool,
            'text': str (original text),
            'normalized': str (if valid)
        }
    """
    import re
    
    # UDSM format: 20XX-04-XXXXX (year 20xx, month 04, sequence 5 digits)
    pattern = config.OCR_REGISTRATION_FORMAT_REGEX  # r"^20\d{2}-04-\d{5}$"
    
    normalized = text.strip().upper()
    
    if re.match(pattern, normalized):
        return {
            'is_valid': True,
            'text': text,
            'normalized': normalized
        }
    else:
        return {
            'is_valid': False,
            'text': text,
            'normalized': None,
            'reason': f'Does not match format {pattern}'
        }
```

**Verify in config.py**:
```python
# kiosk_brain/config.py should have:
OCR_REGISTRATION_FORMAT_REGEX = r"^20\d{2}-04-\d{5}$"
```
✅ Already present (check lines 135–140 of config.py)

---

#### 1.4.2 Combine all pipeline steps (30 min)
**File**: `kiosk_brain/modules/ocr.py`

```python
def process_card_image(image_path):
    """
    Full OCR pipeline: preprocess → extract → validate.
    
    Args:
        image_path (str): Path to card image
    
    Returns:
        dict: {
            'success': bool,
            'registration_number': str or None,
            'confidence': float,
            'raw_text': str,
            'validation': dict,
            'errors': list
        }
    """
    errors = []
    
    try:
        # Step 1: Preprocess
        preprocessed = preprocess_image(image_path)
        if preprocessed is None:
            return {
                'success': False,
                'registration_number': None,
                'errors': ['Preprocessing failed']
            }
        
        # Step 2: Extract with OCR
        ocr_result = extract_registration_number(preprocessed)
        raw_text = ocr_result.get('text', '')
        confidence = ocr_result.get('confidence', 0.0)
        
        if 'error' in ocr_result:
            errors.append(f"OCR error: {ocr_result['error']}")
        
        # Step 3: Validate format
        validation = validate_registration_format(raw_text)
        
        # Step 4: Apply confidence threshold
        min_confidence = config.OCR_TESSERACT_MIN_CONFIDENCE  # 0.85
        
        if validation['is_valid'] and confidence >= min_confidence:
            return {
                'success': True,
                'registration_number': validation['normalized'],
                'confidence': confidence,
                'raw_text': raw_text,
                'validation': validation,
                'errors': errors
            }
        else:
            reason = []
            if not validation['is_valid']:
                reason.append(f"Invalid format: {validation.get('reason', 'unknown')}")
            if confidence < min_confidence:
                reason.append(f"Low confidence: {confidence:.2f} < {min_confidence}")
            
            return {
                'success': False,
                'registration_number': None,
                'confidence': confidence,
                'raw_text': raw_text,
                'validation': validation,
                'errors': errors + reason
            }
    
    except Exception as e:
        return {
            'success': False,
            'registration_number': None,
            'errors': [f"Pipeline error: {str(e)}"]
        }
```

---

### Phase 5: Task 1.5 — Testing and Threshold Calibration (1–1.5 hrs)

**Goal**: Test pipeline against all phone images and calibrate confidence threshold

#### 1.5.1 Create test script
**File**: `kiosk_brain/tests/test_ocr_pipeline.py`

```python
import os
import sys
from pathlib import Path

# Add modules to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.ocr import process_card_image

def test_ocr_pipeline():
    """
    Run OCR pipeline against all test images.
    Record results and generate accuracy report.
    """
    
    test_dir = Path(__file__).parent / 'fixtures' / 'ocr_samples'
    
    if not test_dir.exists():
        print(f"❌ Test directory not found: {test_dir}")
        return
    
    images = sorted(test_dir.glob('card_*.jpg'))
    if not images:
        print(f"❌ No test images found in {test_dir}")
        return
    
    print(f"\n📊 OCR Pipeline Test Report")
    print(f"{'='*70}")
    print(f"Testing {len(images)} images from: {test_dir}\n")
    
    results = []
    accepted = 0
    rejected = 0
    errors = 0
    
    for i, image_path in enumerate(images, 1):
        result = process_card_image(str(image_path))
        results.append(result)
        
        status = "✅ ACCEPT" if result['success'] else "❌ REJECT"
        print(f"{i}. {image_path.name}")
        print(f"   Status: {status}")
        print(f"   Raw Text: '{result.get('raw_text', 'N/A')}'")
        print(f"   Confidence: {result.get('confidence', 0):.2%}")
        
        if result['success']:
            print(f"   ✓ Extracted: {result['registration_number']}")
            accepted += 1
        else:
            for error in result.get('errors', []):
                print(f"   ✗ {error}")
            rejected += 1
        
        print()
    
    # Summary
    print(f"{'='*70}")
    print(f"SUMMARY:")
    print(f"  Total images:  {len(images)}")
    print(f"  Accepted:      {accepted} ({accepted/len(images)*100:.1f}%)")
    print(f"  Rejected:      {rejected} ({rejected/len(images)*100:.1f}%)")
    print(f"  Accuracy:      {accepted/len(images)*100:.1f}%")
    print(f"\n{'='*70}")
    
    # Confidence analysis
    confidences = [r['confidence'] for r in results]
    print(f"\nConfidence Analysis:")
    print(f"  Min: {min(confidences):.2%}")
    print(f"  Max: {max(confidences):.2%}")
    print(f"  Mean: {sum(confidences)/len(confidences):.2%}")
    print(f"\nTarget: >90% accuracy")
    
    if accepted / len(images) >= 0.90:
        print(f"✅ PASSED: Accuracy {accepted/len(images)*100:.1f}% >= 90%")
    else:
        print(f"❌ FAILED: Accuracy {accepted/len(images)*100:.1f}% < 90%")
        print(f"\n💡 Calibration tips:")
        print(f"   - Adjust OCR_BILATERAL_FILTER_SIGMA in config.py (higher = more blur)")
        print(f"   - Adjust OCR_ADAPTIVE_THRESHOLD_C in config.py (higher = more lenient)")
        print(f"   - Adjust OCR_TESSERACT_MIN_CONFIDENCE in config.py (lower threshold)")
        print(f"   - Check ROI_COORDINATES calibration — may need to adjust card region")

if __name__ == '__main__':
    test_ocr_pipeline()
```

#### 1.5.2 Run the test
```bash
cd kiosk_brain
python3 tests/test_ocr_pipeline.py
```

**Expected output**:
```
📊 OCR Pipeline Test Report
======================================================================
Testing 5 images from: tests/fixtures/ocr_samples/

1. card_001.jpg
   Status: ✅ ACCEPT
   Raw Text: '2024-04-12345'
   Confidence: 94.50%
   ✓ Extracted: 2024-04-12345

2. card_002.jpg
   Status: ✅ ACCEPT
   ...

======================================================================
SUMMARY:
  Total images:  5
  Accepted:      5 (100.0%)
  Rejected:      0 (0.0%)
  Accuracy:      100.0%

Target: >90% accuracy
✅ PASSED: Accuracy 100.0% >= 90%
```

---

## 🔧 Troubleshooting Guide

### Issue: Low confidence scores (<70%)
**Cause**: Lighting too harsh, image too blurry, or filter settings too aggressive

**Solution**:
1. Try reducing bilateral filter sigma: `OCR_BILATERAL_FILTER_SIGMA = 50` (was 75)
2. Adjust adaptive threshold: `OCR_ADAPTIVE_THRESHOLD_C = 3` (was 5)
3. Re-capture images with better diffuse lighting

### Issue: Misread characters (e.g., "O" as "0", "l" as "1")
**Cause**: Tesseract character confusion

**Solution**:
1. Verify `OCR_TESSERACT_CHAR_WHITELIST = "0123456789-"` in config.py (constrains to digits only)
2. Increase sharpening kernel effect if characters look soft
3. Check that ROI crop includes full registration number

### Issue: "Format validation failed" but text looks correct
**Cause**: Regex pattern mismatch

**Solution**:
1. Check actual text: `print(result['raw_text'])` and compare to expected format
2. Verify regex pattern in config.py: `OCR_REGISTRATION_FORMAT_REGEX = r"^20\d{2}-04-\d{5}$"`
3. Example valid format: "2024-04-12345" (4-digit year, 2-digit month, 5-digit sequence)

---

## 📦 Deliverables Checklist

- [ ] Phone images captured and organized in `tests/fixtures/ocr_samples/`
- [ ] `preprocess_image()` function complete (Task 1.2)
- [ ] `extract_registration_number()` function complete (Task 1.3)
- [ ] `validate_registration_format()` function complete (Task 1.4)
- [ ] `process_card_image()` wrapper function complete
- [ ] `test_ocr_pipeline.py` test script complete (Task 1.5)
- [ ] All tests passing with >90% accuracy
- [ ] Confidence threshold tuned and documented
- [ ] All code committed to git with meaningful messages

---

## 🎬 Next Steps After This Phase

Once Task 1.5 is complete:
1. **Phase 4.6 Integration**: Wire OCR pipeline to Kivy UI (batch progress display)
2. **Phase 5 Hardware**: Physical camera mounting at Conveyor 1 scan station
3. **Phase 5 Firmware**: STM32 SPI communication for reject bin servo actuation
4. **End-to-End Testing**: Full kiosk workflow with real card scanning

---

## 📝 Quick Reference

### Key Files
- `kiosk_brain/modules/ocr.py` — All OCR functions here
- `kiosk_brain/config.py` — All tunable parameters
- `kiosk_brain/tests/fixtures/ocr_samples/` — Phone images go here
- `kiosk_brain/tests/test_ocr_pipeline.py` — Test script (create this)

### Key Config Parameters to Know
```python
OCR_FRAME_RESOLUTION = (2560, 1440)           # For camera (not phone images)
OCR_BILATERAL_FILTER_D = 11                   # Kernel size
OCR_BILATERAL_FILTER_SIGMA = 75               # Blur strength (tune this)
OCR_ADAPTIVE_THRESHOLD_BLOCKSIZE = 11         # Block size for threshold
OCR_ADAPTIVE_THRESHOLD_C = 5                  # Threshold constant (tune this)
OCR_CANNY_THRESHOLD1 = 100                    # Canny edge detection
OCR_CANNY_THRESHOLD2 = 200
OCR_TESSERACT_PSM = 7                         # Single line mode
OCR_TESSERACT_CHAR_WHITELIST = "0123456789-" # Digits + hyphen only
OCR_TESSERACT_MIN_CONFIDENCE = 0.85           # 85% minimum (tune this)
OCR_REGISTRATION_FORMAT_REGEX = r"^20\d{2}-04-\d{5}$"  # Validation regex
OCR_ROI_COORDINATES = (300, 50, 200, 50)     # (x, y, w, h) — calibrate this
```

### Useful Commands
```bash
# Test preprocessing on single image
python3 -c "
from modules.ocr import preprocess_image
import cv2
img = preprocess_image('tests/fixtures/ocr_samples/card_001.jpg')
print(f'Shape: {img.shape}, dtype: {img.dtype}')
"

# Run full test suite
python3 tests/test_ocr_pipeline.py

# View git status
git status

# Commit changes
git add kiosk_brain/modules/ocr.py kiosk_brain/tests/test_ocr_pipeline.py
git commit -m "feat: implement Phase 1 OCR pipeline (preprocessing, Tesseract, validation)"
```

---

**Questions?** Refer back to BUILD.md (Tasks 1.2–1.5) or conversation history for context.

**Ready to start?** Capture your 5 phone images, organize them, and run Phase 2 (preprocessing implementation).
