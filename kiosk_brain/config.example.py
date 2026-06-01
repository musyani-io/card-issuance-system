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
# UNIVERSITY DATABASE API
# ============================================================================

UNIVERSITY_API_BASE_URL = "http://localhost:5000"  # Mock server (localhost for testing)
UNIVERSITY_API_KEY = "test-key-12345"  # Must match mock_db_api/config.py

# ==========================================================================
# IMAGE PROCESSING (Phase 1 OCR)
# ==========================================================================
# These values are safe defaults for development. Change them to match your
# card layout, image quality, and OCR performance needs.

CARD_DETECTION = {
    "canny_threshold1": 50,          # Lower edge threshold; higher = fewer edges.
    "canny_threshold2": 150,         # Upper edge threshold; higher = stricter edges.
    "blur_ksize": (5, 5),            # Blur before edge detection; reduces noise.
    "morph_kernel": (5, 5),          # Close/dilate gaps in edges; helps broken contours.
    "dilate_iterations": 1,          # More iterations thickens edges more.
    "target_width": 1000,            # Resize working image width; stabilizes detection.
    "min_area_abs": 1000,            # Smallest contour area allowed.
    "min_area_ratio": 0.03,          # Smallest contour as fraction of image area.
    "max_area_ratio": 0.9,           # Largest contour as fraction of image area.
    "expected_aspect_ratio": 88.0 / 55.0,  # Typical CR80 card ratio; rejects odd shapes.
    "aspect_ratio_tolerance": 0.25,   # Allowed deviation from expected card ratio.
    "approx_epsilon": 0.02,           # Polygon simplification strength; lower keeps more points.
}

PERSPECTIVE = {
    "output_size": (880, 550),       # Flattened card size; changes final warp resolution.
}

OCR_PREPROCESS = {
    "gaussian_ksize": (5, 5),        # Smooths ROI before thresholding; reduces speckle.
    "adaptive_block_size": 51,       # Local window size for thresholding; must be odd.
    "adaptive_C": 5,                 # Threshold offset; higher = more white pixels.
    "morph_kernel": (3, 3),          # Cleans small noise after thresholding.
}

ROI = {
    "default": (0.009, 0.54, 0.28, 0.08),  # Card-area ROI (x, y, w, h) in relative fractions.
}

PRE_OCR = {
    "blur_ksize": (3, 3),            # Mild blur before OCR; softens remaining noise.
    "sharpen_kernel": [[0, -1, 0], [-1, 5, -1], [0, -1, 0]],  # Sharpens text edges before OCR.
}
