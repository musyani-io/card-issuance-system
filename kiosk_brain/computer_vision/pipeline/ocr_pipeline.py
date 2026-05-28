import time
from typing import Dict, Optional, List

import cv2
import pytesseract

from ..core.card_detector import detect_card
from ..core.perspective_corrector import straighten_card
from ..core.anchor_roi import find_anchor_box, derive_rois_from_anchor
from ..core.image_utils import preprocess_for_ocr, resize_image
from ..core.student_id_validator import extract_registration_number_robust
from ..core.exceptions import (
    CardNotFoundError,
    CardDetectionAmbiguousError,
    OCRExtractionError,
    PerspectiveCorrectionError,
    InvalidStudentIDError,
)


class CardOCRPipeline:
    def __init__(self, config: Dict):
        self.config = config

    def _log(self, message: str) -> None:
        if self.config.get("DEBUG", {}).get("verbose_logging", False):
            print(message)

    def scan_card(self, image) -> Dict:
        """
        Main card scanning pipeline. Orchestrates all processing stages.
        
        Returns:
            Dict with success status, extracted fields, and metadata
        """
        start = time.perf_counter()

        # Input validation
        if image is None or getattr(image, "size", 0) == 0:
            return self._result(
                False,
                None,
                None,
                None,
                None,
                0.0,
                "input",
                "Invalid input image: None or empty",
                start,
            )

        # Convert grayscale to BGR if needed
        if len(image.shape) == 2:
            image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)

        # Resize if too large
        max_width = self.config.get("MAX_INPUT_WIDTH")
        if max_width:
            try:
                image = resize_image(image, max_width=int(max_width))
            except Exception as e:
                return self._result(
                    False,
                    None,
                    None,
                    None,
                    None,
                    0.0,
                    "preprocess",
                    f"Resize failed: {e}",
                    start,
                )

        # Stage 1: Card Detection
        try:
            corners = detect_card(image)
        except (CardNotFoundError, CardDetectionAmbiguousError) as e:
            return self._result(False, None, None, None, None, 0.0, "card_detection", str(e), start)

        if corners is None:
            return self._result(False, None, None, None, None, 0.0, "card_detection", "No card detected", start)

        # Stage 2: Perspective Correction
        try:
            straight = straighten_card(image, corners)
        except Exception as e:
            return self._result(
                False,
                None,
                None,
                None,
                None,
                0.0,
                "perspective",
                str(PerspectiveCorrectionError(str(e))),
                start,
            )

        # Stage 3: Anchor Detection
        anchor_box = find_anchor_box(
            straight,
            anchor_texts=self.config["ANCHOR_OCR"]["anchor_texts"],
            min_confidence=self.config["ANCHOR_OCR"]["min_confidence"],
            psm=self.config["ANCHOR_OCR"]["psm"],
            oem=self.config["ANCHOR_OCR"]["oem"],
            char_whitelist=self.config["ANCHOR_OCR"]["char_whitelist"],
        )

        if anchor_box is None:
            return self._result(False, None, None, None, None, 0.0, "anchor", "Anchor not found", start)

        # Stage 4: Derive ROI Positions
        derived = derive_rois_from_anchor(straight, anchor_box, self.config["ANCHOR_ROI_OFFSETS"])
        
        if "registration_number" not in derived:
            return self._result(False, None, None, None, None, 0.0, "roi", "registration_number ROI not found", start)

        # Stage 5: Extract All Fields
        extracted_fields = {}

        # Extract registration_number
        registration_number_roi = self._crop_roi_by_ratio(straight, derived["registration_number"])
        registration_number_pre = preprocess_for_ocr(registration_number_roi, self.config.get("PREPROCESSING"))
        registration_number_texts = self._run_ocr_strategies(registration_number_pre)
        registration_number = extract_registration_number_robust(
            registration_number_texts,
            self.config["STUDENT_ID_PATTERN"],
            self.config["VALID_YEAR_RANGE"],
            self.config["ID_TOTAL_LENGTH"],
        )

        if not registration_number:
            return self._result(
                False,
                None,
                None,
                None,
                None,
                0.0,
                "ocr",
                str(InvalidStudentIDError("Registration number not found")),
                start,
            )

        extracted_fields["registration_number"] = registration_number

        # COMMENTED OUT: Focus on registration_number extraction only
        # # Extract name (if ROI available)
        # if "name" in derived:
        #     name_roi = self._crop_roi_by_ratio(straight, derived["name"])
        #     name_pre = preprocess_for_ocr(name_roi, self.config.get("PREPROCESSING"))
        #     name_texts = self._run_ocr_strategies(name_pre)
        #     # Use first valid OCR result for name
        #     extracted_fields["name"] = next((t.strip() for t in name_texts if t.strip()), None)

        # # Extract program (if ROI available)
        # if "program" in derived:
        #     program_roi = self._crop_roi_by_ratio(straight, derived["program"])
        #     program_pre = preprocess_for_ocr(program_roi, self.config.get("PREPROCESSING"))
        #     program_texts = self._run_ocr_strategies(program_pre)
        #     extracted_fields["program"] = next((t.strip() for t in program_texts if t.strip()), None)

        # # Extract expiry_date (if ROI available)
        # if "expiry_date" in derived:
        #     expiry_date_roi = self._crop_roi_by_ratio(straight, derived["expiry_date"])
        #     expiry_date_pre = preprocess_for_ocr(expiry_date_roi, self.config.get("PREPROCESSING"))
        #     expiry_date_texts = self._run_ocr_strategies(expiry_date_pre)
        #     extracted_fields["expiry_date"] = next((t.strip() for t in expiry_date_texts if t.strip()), None)

        return self._result(
            True,
            extracted_fields.get("registration_number"),
            None,  # name extraction disabled
            None,  # program extraction disabled
            None,  # expiry_date extraction disabled
            1.0,
            "ocr",
            None,
            start,
        )

    def _run_ocr_strategies(self, image) -> List[str]:
        """
        Try multiple Tesseract configurations for robust OCR.
        """
        configs = []
        base = self.config["TESSERACT_CONFIG_STRING"]
        configs.append(base)

        alt_psm = 7
        configs.append(
            f"--psm {alt_psm} --oem {self.config['TESSERACT_CONFIG']['oem']} "
            f"-c tessedit_char_whitelist={self.config['TESSERACT_CONFIG']['char_whitelist']}"
        )

        inv = cv2.bitwise_not(image)
        texts = []
        for cfg in configs:
            texts.append(pytesseract.image_to_string(image, config=cfg))
            texts.append(pytesseract.image_to_string(inv, config=cfg))

        return texts

    @staticmethod
    def _crop_roi_by_ratio(image, roi):
        """
        Crop ROI using normalized ratios.
        """
        h, w = image.shape[:2]
        x1 = int(roi["x_start"] * w)
        x2 = int(roi["x_end"] * w)
        y1 = int(roi["y_start"] * h)
        y2 = int(roi["y_end"] * h)
        return image[y1:y2, x1:x2]

    def _result(
        self,
        success: bool,
        registration_number: Optional[str],
        name: Optional[str],
        program: Optional[str],
        expiry_date: Optional[str],
        confidence: float,
        method: str,
        error: Optional[str],
        start_time: float,
    ) -> Dict:
        """
        Build standardized result dictionary.
        """
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        return {
            "success": success,
            "registration_number": registration_number,
            "name": name,
            "program": program,
            "expiry_date": expiry_date,
            "confidence": confidence,
            "method": method,
            "error": error,
            "processing_time_ms": elapsed_ms,
        }
