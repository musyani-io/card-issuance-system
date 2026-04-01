"""
OCR Pipeline for ID Card Registration Number Extraction

This module implements the complete vision pipeline for extracting registration numbers from printed ID cards:
- Camera frame capture and preprocessing (gamma correction, denoising)
- Card region detection and perspective correction
- Text extraction via Tesseract OCR with confidence filtering
- Multi-attempt retry with automatic quality feedback

**PHASE 1 IMPLEMENTATION:** Target >90% success rate on UDSM ID cards.

Architecture: Three-Stage Pipeline
==================================

STAGE 1: IMAGE ACQUISITION & PREPROCESSING
    - Capture 1280x720 frames from Pi Camera Module 3
    - Apply bilateral filter (noise reduction, edge preservation)
    - Histogram equalization (contrast enhancement)
    - Gamma correction for lighting variation compensation

STAGE 2: CARD REGION LOCALIZATION
    - Detect blue ID card border (HSV color space)
    - Apply Canny edge detection
    - Perspective transform correction (homography)
    - Crop to registration number region (bottom-left quadrant)

STAGE 3: OCR & VALIDATION
    - Tesseract with UDSM reg number config (format: T2MMXX-XXX)
    - Confidence threshold gating (minimum 0.85 confidence)
    - Format validation regex: ^[A-Z]\\d[A-Z]{2}\\d{2}-\\d{3}$
    - Automatic frame queue retry on low confidence

Planned Functions:
==================

- preprocess_frame(frame) - Bilateral filter + histogram equalization + gamma correction
- detect_card_region(frame) - Border detection, perspective correction, region crop
- extract_registration_number(frame, min_confidence=0.85) - Tesseract OCR + format validation
- process_with_retry(max_attempts=3) - Queue-based retry with confidence feedback
"""
