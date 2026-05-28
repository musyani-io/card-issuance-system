"""Computer Vision module for card detection and OCR."""
__version__ = "1.0.0"

from .pipeline.ocr_pipeline import CardOCRPipeline
from .core.exceptions import (
    CardNotFoundError,
    CardDetectionAmbiguousError,
    OCRExtractionError,
    PerspectiveCorrectionError,
    InvalidStudentIDError,
)

__all__ = [
    "CardOCRPipeline",
    "CardNotFoundError",
    "CardDetectionAmbiguousError",
    "OCRExtractionError",
    "PerspectiveCorrectionError",
    "InvalidStudentIDError",
]
