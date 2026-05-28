"""
OCR Configuration for Registration Card System
Based on physical measurements from card layout
University Card - 2024 Edition Cards
"""

# Card Physical Specifications
CARD_PHYSICAL = {
    "width_mm": 88,
    "height_mm": 55,
    "standard": "CR80",  # Close to CR80 standard (85.60×53.98mm)
}

# Standard output size for perspective-corrected cards
# Maintains aspect ratio: 88/55 = 1.6
# Resolution: 10 pixels per mm
CARD_OUTPUT_SIZE = (880, 550)  # Width × Height in pixels

# Anchor-based ROI detection (optional)
# Uses a detected anchor label (e.g., "NAME") and applies offsets
# Offsets are fractions of card width/height relative to anchor top-left.
ANCHOR_OCR = {
    "anchor_texts": ["NAME"],  # Update to the exact printed label on your card
    "min_confidence": 50,
    "psm": 6,
    "oem": 3,
    "char_whitelist": "ABCDEFGHIJKLMNOPQRSTUVWXYZ: ",
}

# Offsets relative to anchor top-left (fractions of card width/height)
# Anchor aligns with the name line.
ANCHOR_ROI_OFFSETS = {
    "name": {
        "dx": -0.008,
        "dy": 0.064,
        "w": 0.648,
        "h": 0.073,
    },
    "registration_number": {
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

# Registration Number Validation Rules
STUDENT_ID_PATTERN = r"\d{4}-04-\d{5}"  # Format: 20XX-04-XXXXX (fixed April)
VALID_YEAR_RANGE = (2015, 2030)
ID_TOTAL_LENGTH = 13  # Including hyphens

# Card Detection Parameters
CARD_DETECTION = {
    "min_area": 10000,  # Minimum contour area in pixels
    "max_area": 5000000,  # Maximum contour area in pixels (increased for high-res images)
    "aspect_ratio": 1.6,  # Expected aspect ratio (88/55)
    "aspect_ratio_tolerance": 1.0,  # Allowed deviation (increased for detection)
    "canny_threshold1": 30,  # Lower threshold for Canny edge detection (lowered)
    "canny_threshold2": 100,  # Upper threshold for Canny edge detection (lowered)
}

# OCR Settings (Tesseract)
TESSERACT_CONFIG = {
    "psm": 6,  # Page Segmentation Mode: Assume uniform block of text
    "oem": 3,  # OCR Engine Mode: Default (LSTM + Legacy)
    "char_whitelist": "0123456789-",  # Only digits and hyphens for registration_number
}

# Build complete Tesseract config string
TESSERACT_CONFIG_STRING = (
    f"--psm {TESSERACT_CONFIG['psm']} "
    f"--oem {TESSERACT_CONFIG['oem']} "
    f"-c tessedit_char_whitelist={TESSERACT_CONFIG['char_whitelist']}"
)

# Font Properties (for reference)
FONT_PROPERTIES = {
    "name": "Calibri",
    "size_pt": 9,
    "style": "Bold",
    "color": "Blue",  # Text color (may need color-specific preprocessing)
}

# Preprocessing Parameters
PREPROCESSING = {
    "enable_denoise": False,
    "enable_contrast": True,
    "enable_binarize": True,
    "denoise_strength": 10,  # fastNlMeansDenoising strength
    "clahe_clip_limit": 2.0,  # CLAHE contrast limit
    "clahe_tile_grid_size": (8, 8),  # CLAHE tile size
    "gaussian_blur_kernel": (5, 5),  # Gaussian blur kernel size
    "binary_threshold_blocksize": 11,  # Adaptive threshold block size
    "binary_threshold_c": 2,  # Adaptive threshold constant
}

# Performance Settings
MAX_INPUT_WIDTH = 800  # Resize input if wider than this
MAX_RETRIES = 3  # Maximum OCR retry attempts
PROCESSING_TIMEOUT_MS = 2000  # Maximum processing time per card
CONFIDENCE_THRESHOLD = 0.7  # Minimum confidence score to accept result

# Known Challenges (for reference)
CHALLENGES = [
    "Low contrast text (blue on white)",
    "Glossy surface causing glare",
    "Background watermark interference",
    "Colored text (not black)",
    "Card edge wear",
    "Multiple text regions close together",
]

# Debug Settings
DEBUG = {
    "save_intermediate_images": False,  # Save preprocessing steps
    "debug_output_dir": "data/debug_outputs",
    "verbose_logging": False,
}
