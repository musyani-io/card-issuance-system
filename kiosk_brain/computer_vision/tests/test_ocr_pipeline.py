import unittest
import cv2
import numpy as np
from pathlib import Path
from ..config.ocr_config import *
from ..pipeline.ocr_pipeline import CardOCRPipeline
from ..core.exceptions import *
from ..core.card_detector import detect_card, order_points
from ..core.perspective_corrector import straighten_card
from ..core.student_id_validator import (
    extract_registration_number_robust,
    validate_registration_number,
    extract_registration_number,
)


class TestCardDetection(unittest.TestCase):
    """Test card detection functionality."""

    def test_order_points_consistency(self):
        """Test that points are ordered correctly."""
        # Test points: TL, TR, BR, BL (randomly ordered)
        pts = np.array([[100, 100], [300, 100], [300, 200], [100, 200]], dtype=np.float32)
        ordered = order_points(pts)
        
        # Verify 4 points returned
        self.assertEqual(ordered.shape, (4, 2))
        
        # Verify dtype
        self.assertEqual(ordered.dtype, np.float32)


class TestRegistrationNumberExtraction(unittest.TestCase):
    """Test registration number extraction and validation."""

    def test_extract_valid_registration_number(self):
        """Test extraction of valid registration number."""
        text = "2024-04-12345"
        pattern = STUDENT_ID_PATTERN
        result = extract_registration_number(text, pattern)
        self.assertEqual(result, "2024-04-12345")

    def test_validate_registration_number_valid_format(self):
        """Test validation of valid registration number format."""
        reg_number = "2024-04-12345"
        is_valid = validate_registration_number(
            reg_number,
            STUDENT_ID_PATTERN,
            VALID_YEAR_RANGE,
            ID_TOTAL_LENGTH,
        )
        self.assertTrue(is_valid)

    def test_validate_registration_number_invalid_month(self):
        """Test rejection of invalid month."""
        reg_number = "2024-05-12345"  # Wrong month (not 04)
        is_valid = validate_registration_number(
            reg_number,
            STUDENT_ID_PATTERN,
            VALID_YEAR_RANGE,
            ID_TOTAL_LENGTH,
        )
        self.assertFalse(is_valid)

    def test_validate_registration_number_invalid_year(self):
        """Test rejection of invalid year."""
        reg_number = "2010-04-12345"  # Year out of range
        is_valid = validate_registration_number(
            reg_number,
            STUDENT_ID_PATTERN,
            VALID_YEAR_RANGE,
            ID_TOTAL_LENGTH,
        )
        self.assertFalse(is_valid)

    def test_extract_registration_number_robust_single_valid(self):
        """Test robust extraction with single valid text."""
        texts = ["2024-04-12345"]
        result = extract_registration_number_robust(
            texts,
            STUDENT_ID_PATTERN,
            VALID_YEAR_RANGE,
            ID_TOTAL_LENGTH,
        )
        self.assertEqual(result, "2024-04-12345")

    def test_extract_registration_number_robust_multiple_texts(self):
        """Test robust extraction with multiple OCR attempts."""
        texts = [
            "2024-04-12345",
            "2024-04-12345",
            "invalid",
            "2024-04-12345",
        ]
        result = extract_registration_number_robust(
            texts,
            STUDENT_ID_PATTERN,
            VALID_YEAR_RANGE,
            ID_TOTAL_LENGTH,
        )
        # Should return most frequent valid result
        self.assertEqual(result, "2024-04-12345")

    def test_extract_registration_number_robust_no_valid(self):
        """Test robust extraction with no valid IDs."""
        texts = ["invalid", "also invalid", "2010-04-12345"]
        result = extract_registration_number_robust(
            texts,
            STUDENT_ID_PATTERN,
            VALID_YEAR_RANGE,
            ID_TOTAL_LENGTH,
        )
        self.assertIsNone(result)


class TestOCRPipeline(unittest.TestCase):
    """Test OCR pipeline orchestration."""

    def setUp(self):
        """Set up test configuration."""
        self.config = {
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
        self.pipeline = CardOCRPipeline(self.config)

    def test_pipeline_initialization(self):
        """Test pipeline initializes correctly."""
        self.assertIsNotNone(self.pipeline)
        self.assertEqual(self.pipeline.config, self.config)

    def test_pipeline_invalid_input(self):
        """Test pipeline handles invalid input."""
        result = self.pipeline.scan_card(None)
        self.assertFalse(result["success"])
        self.assertIn("Invalid input image", result["error"])

    def test_pipeline_blank_image(self):
        """Test pipeline handles blank image (no card)."""
        blank_image = np.ones((480, 640, 3), dtype=np.uint8) * 255
        result = self.pipeline.scan_card(blank_image)
        # Should fail at card detection
        self.assertFalse(result["success"])

    def test_pipeline_result_format(self):
        """Test that pipeline returns correct result format."""
        blank_image = np.ones((480, 640, 3), dtype=np.uint8) * 255
        result = self.pipeline.scan_card(blank_image)
        
        # Check result dictionary keys
        expected_keys = {
            "success",
            "registration_number",
            "name",
            "program",
            "expiry_date",
            "confidence",
            "method",
            "error",
            "processing_time_ms",
        }
        self.assertEqual(set(result.keys()), expected_keys)

        # Check types
        self.assertIsInstance(result["success"], bool)
        self.assertIsInstance(result["processing_time_ms"], float)


class TestImageUtils(unittest.TestCase):
    """Test image utility functions."""

    def test_image_conversion_functions(self):
        """Test basic image conversion functions exist."""
        from ..core.image_utils import (
            convert_to_grayscale,
            resize_image,
            enhance_contrast,
            denoise_image,
            binarize_image,
            preprocess_for_ocr,
        )
        
        # Create test image
        test_image = np.random.randint(0, 256, (480, 640, 3), dtype=np.uint8)
        
        # Test grayscale conversion
        gray = convert_to_grayscale(test_image)
        self.assertEqual(len(gray.shape), 2)
        
        # Test resize
        resized = resize_image(test_image, max_width=400)
        self.assertLessEqual(resized.shape[1], 400)
        
        # Test preprocessing chain
        preprocessed = preprocess_for_ocr(test_image, PREPROCESSING)
        self.assertEqual(len(preprocessed.shape), 2)


if __name__ == '__main__':
    unittest.main()
