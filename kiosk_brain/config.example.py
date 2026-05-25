"""
Configuration Template for Kiosk Brain

SETUP INSTRUCTIONS:
===================
1. Copy this file to config.py:
       cp config.example.py config.py

2. Edit config.py with YOUR actual credentials (NEVER commit sensitive data)

CREDENTIAL SOURCES:
===================
- BRIQ SMS Gateway: https://briq.tz (Tanzanian SMS provider)
- Gmail App Password: https://myaccount.google.com/apppasswords
- OCR settings: Calibrated during Phase 1 testing
"""

# ============================================================================
# SMS GATEWAY (BRIQ Solutions)
# ============================================================================

BRIQ_API_KEY = "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"  # Bearer token from BRIQ dashboard
BRIQ_SENDER_ID = "CARD KIOSK"  # Message sender identifier
BRIQ_BASE_URL = "https://karibu.briq.tz"  # SMS API endpoint

# ============================================================================
# EMAIL GATEWAY (Gmail SMTP)
# ============================================================================

SMTP_EMAIL = "smartcard.kiosk@gmail.com"  # Gmail account for sending credentials

APP_PASSWORD = "xxxx xxxx xxxx xxxx"  # Gmail 16-character app-specific password
# SETUP: Go to https://myaccount.google.com/apppasswords
# (Requires 2-Step Verification enabled)

# ============================================================================
# OCR CONFIGURATION (PHASE 1)
# ============================================================================
"""
Camera and OCR pipeline settings for student ID card registration number extraction.

TASK 1.1: CAMERA CAPTURE & VALIDATION
    - OCR_FRAME_RESOLUTION: Capture resolution for Pi Camera
    - OCR_FRAME_RATE: Target frame rate (30 fps = standard)

TASK 1.1.4: ROI CALIBRATION
    - OCR_ROI_COORDINATES: (x1, y1, x2, y2) pixel bounding box for registration number
    - Format: Left-center region where registration number is printed
    - Calibrated after first capture test

TASK 1.2: IMAGE PREPROCESSING
    - Bilateral filter for noise reduction while preserving edges
    - Adaptive threshold for contrast enhancement
    - Canny edge detection for contour extraction

TASK 1.3: TESSERACT OCR
    - PSM 7 = single text line (best for registration numbers)
    - Whitelist to extract only digits and hyphens
    - Min confidence threshold (0.85 = 85%)

TASK 1.4: VALIDATION
    - OCR_REGISTRATION_FORMAT_REGEX: UDSM format pattern (20xx-04-xxxxx)
"""

# TASK 1.1: Frame capture workflow
OCR_FRAME_RESOLUTION = (2560, 1440)  # (width, height) - QHD for better text clarity
OCR_FRAME_RATE = 30  # fps

# TASK 1.1.4: ROI (Region of Interest) calibration
# PLACEHOLDER: Will be calibrated after first capture test (Task 1.1.4)
# Format: (x1, y1, x2, y2) - pixel coordinates of bounding box
# Example (to be replaced): (150, 250, 400, 300)
OCR_ROI_COORDINATES = None

# TASK 1.2: Image preprocessing parameters
OCR_BILATERAL_FILTER_D = 11  # Pixel diameter for bilateral filter
OCR_BILATERAL_FILTER_SIGMA = 75  # Sigma for color/spatial filtering
OCR_ADAPTIVE_THRESHOLD_BLOCKSIZE = 11  # Gaussian kernel size (must be odd)
OCR_ADAPTIVE_THRESHOLD_C = 5  # Constant subtracted from mean
OCR_CANNY_THRESHOLD1 = 100  # Lower threshold for Canny edge detection
OCR_CANNY_THRESHOLD2 = 200  # Upper threshold for Canny edge detection
OCR_GAUSS_BLUR_KERNEL = (3, 3)  # Gaussian blur kernel (must be odd)
OCR_SHARPEN_KERNEL = None  # Dynamic: [[0, -1, 0], [-1, 5, -1], [0, -1, 0]]

# TASK 1.3: Tesseract OCR configuration
OCR_TESSERACT_PSM = 7  # PSM 7 = single text line (for registration numbers)
OCR_TESSERACT_CHAR_WHITELIST = "0123456789-"  # Only digits and hyphen
OCR_TESSERACT_MIN_CONFIDENCE = 0.85  # Confidence threshold (0.0–1.0)

# TASK 1.4: Format validation
OCR_REGISTRATION_FORMAT_REGEX = r"^20\d{2}-04-\d{5}$"  # UDSM: 20xx-04-xxxxx
OCR_REGISTRATION_FORMAT_DESCRIPTION = "UDSM format: 20xx-04-xxxxx (e.g., 2022-04-09050)"
