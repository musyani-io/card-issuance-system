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
    - Crop to registration number region (left-center quadrant)

STAGE 3: OCR & VALIDATION
    - Tesseract with UDSM reg number config (format: 20xx-04-xxxxx)
    - Confidence threshold gating (minimum 0.85 confidence)
    - Format validation regex: ^20\\d{2}-04-\\d{5}$
    - Automatic frame queue retry on low confidence

Key Functions:
==============
- CameraCapture class - Pi Camera Module 3 interface with capture_frame()
- preprocess_frame(frame) - Bilateral filter + histogram equalization + gamma correction
- detect_card_region(frame) - Border detection, perspective correction, region crop
- extract_registration_number(frame, min_confidence=0.85) - Tesseract OCR + format validation
- validate_registration_format(text: str) - Regex validation for 20xx-04-xxxxx format
- process_with_retry(max_attempts=3) - Queue-based retry with confidence feedback

TASK 1.1: CAMERA CAPTURE & LIGHTING VALIDATION
===============================================
This phase validates:
1. Camera functional: capture raw frames at 1280x720
2. Lighting adequate: registration number readable in captured frames
3. ROI calibration: registration number location identified in pixel coordinates
"""

import cv2
import logging
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, Tuple, Any
import os
import time
import subprocess
import tempfile
import io

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Check if rpicam-still (libcamera CLI tool) is available
RPICAM_AVAILABLE = os.path.exists('/usr/bin/rpicam-still')

# Try to import picamera2 (fallback, not primary)
try:
    from picamera2 import Picamera2
    PICAMERA2_AVAILABLE = True
except ImportError:
    PICAMERA2_AVAILABLE = False

# Check if we're in SSH mode (no display)
DISPLAY_AVAILABLE = os.environ.get('DISPLAY') is not None
SSH_MODE = not DISPLAY_AVAILABLE

if RPICAM_AVAILABLE:
    logger.info("✓ rpicam-still detected - will use for primary camera capture")
elif PICAMERA2_AVAILABLE:
    logger.info("✓ picamera2 available - will use as fallback")
else:
    logger.warning("No camera libraries available - will use OpenCV fallback")


class CameraCapture:
    """
    Interface to Pi Camera via picamera2 (v3) or picamera (v2).
    
    Provides:
    - Frame capture at configurable resolution
    - Support for Pi Camera v2 and v3
    - Fallback to OpenCV cv2.VideoCapture for testing on non-Pi systems
    - Frame storage to disk for inspection
    - Metadata logging (timestamp, focus quality indicator)
    - SSH mode detection (no display available)
    
    TASK 1.1.1: Verify camera functional
    TASK 1.1.2: Design capture workflow (resolution, trigger mode)
    """
    
    def __init__(self, resolution: Tuple[int, int] = (1280, 720), camera_index: int = 0, camera_version: Optional[str] = None):
        """
        Initialize camera capture interface.
        
        Args:
            resolution (Tuple[int, int]): Frame dimensions (width, height). Default 1280x720.
            camera_index (int): Camera device index (0 = primary).
            camera_version (str): Force camera version ('rpicam', 'picamera2', 'opencv').
                                 If None, auto-detect based on available tools.
        """
        self.resolution = resolution
        self.camera_index = camera_index
        self.camera = None
        self.temp_frame_file = None
        self.frame_count = 0
        self.is_ssh_mode = SSH_MODE
        
        # Auto-detect camera version if not specified
        if camera_version is None:
            if RPICAM_AVAILABLE:
                self.camera_version = 'rpicam'
            elif PICAMERA2_AVAILABLE:
                self.camera_version = 'picamera2'
            else:
                self.camera_version = 'opencv'
        else:
            self.camera_version = camera_version
        
        logger.info(f"Initializing CameraCapture: resolution={resolution}, camera_version={self.camera_version}, ssh_mode={self.is_ssh_mode}")
        
        # Initialize camera based on version
        if self.camera_version == 'rpicam' and RPICAM_AVAILABLE:
            self._init_rpicam()
        elif self.camera_version == 'picamera2' and PICAMERA2_AVAILABLE:
            self._init_picamera2()
        else:
            self._init_opencv()
    
    def _init_picamera2(self):
        """Initialize picamera2 for Pi Camera Module 3 (CSI port, Bookworm OS)."""
        try:
            self.camera = Picamera2(camera_num=self.camera_index)
            
            # Configure preview (camera tuning)
            preview_config = self.camera.create_preview_configuration(
                main={"format": "BGR888", "size": self.resolution}
            )
            self.camera.configure(preview_config)
            self.camera.start()
            
            logger.info(f"✓ picamera2 (Pi Camera v3) initialized: {self.resolution}, camera_num={self.camera_index}")
        except Exception as e:
            logger.error(f"picamera2 initialization failed: {e}. Falling back to OpenCV.")
            self.camera_version = None
            self._init_opencv()
    
    def _init_rpicam(self):
        """Initialize libcamera via rpicam-still (command-line tool)."""
        try:
            # Test rpicam-still is accessible
            result = subprocess.run(['rpicam-still', '--help'], capture_output=True, timeout=5)
            if result.returncode == 0:
                # Create temp file for frame storage
                self.temp_frame_file = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
                self.temp_frame_file.close()
                logger.info(f"✓ rpicam-still initialized: {self.resolution}")
                return
        except Exception as e:
            logger.error(f"rpicam-still initialization failed: {e}")
        
        # Fallback to picamera2 if available
        if PICAMERA2_AVAILABLE:
            logger.info("Falling back to picamera2")
            self.camera_version = 'picamera2'
            self._init_picamera2()
        else:
            logger.info("Falling back to OpenCV")
            self.camera_version = 'opencv'
            self._init_opencv()
    
    def _init_picamera(self):
        """Initialize picamera for Pi Camera v2 (CSI port, older Raspberry Pi OS)."""
        try:
            self.camera = picamera.PiCamera(camera_num=self.camera_index)
            self.camera.resolution = self.resolution
            self.camera.framerate = 30
            
            # Allow time for camera to warm up
            time.sleep(2)
            
            logger.info(f"✓ picamera (Pi Camera v2) initialized: {self.resolution}")
        except Exception as e:
            logger.error(f"picamera initialization failed: {e}. Falling back to OpenCV.")
            self.camera_version = None
            self._init_opencv()
    
    def _init_opencv(self):
        """Initialize OpenCV cv2.VideoCapture (fallback for testing on non-Pi systems)."""
        try:
            self.camera = cv2.VideoCapture(self.camera_index)
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.resolution[0])
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.resolution[1])
            self.camera.set(cv2.CAP_PROP_FPS, 30)
            
            # Test if camera is accessible
            ret, _ = self.camera.read()
            if not ret:
                raise RuntimeError("cv2.VideoCapture.read() returned False - camera may not be accessible")
            
            logger.info(f"✓ OpenCV VideoCapture initialized: {self.resolution}")
        except Exception as e:
            logger.error(f"OpenCV VideoCapture initialization failed: {e}")
            self.camera = None
    
    def is_ready(self) -> bool:
        """Check if camera is initialized and ready to capture."""
        if self.camera_version == 'rpicam':
            return self.temp_frame_file is not None
        return self.camera is not None
    
    def capture_frame(self, save_to_disk: bool = False, output_dir: Optional[str] = None) -> Optional[np.ndarray]:
        """
        Capture a single frame from the camera.
        
        Args:
            save_to_disk (bool): If True, save captured frame to disk with timestamp
            output_dir (str): Directory to save frames. If None, creates 'tests/fixtures/ocr_frames/' in project root.
        
        Returns:
            np.ndarray: Captured frame (BGR format, shape HxWx3), or None if capture fails
            
        TASK 1.1.1: Used to verify camera is functional
        """
        try:
            if self.camera_version == 'rpicam' and RPICAM_AVAILABLE:
                # Capture via rpicam-still to JPEG file
                cmd = [
                    'rpicam-still',
                    '-o', self.temp_frame_file.name,
                    '--width', str(self.resolution[0]),
                    '--height', str(self.resolution[1]),
                    '-t', '100',  # 100ms exposure/timeout
                    '--nopreview'  # No preview window (headless safe)
                ]
                result = subprocess.run(cmd, capture_output=True, timeout=5)
                
                if result.returncode == 0:
                    # Read JPEG from disk into numpy array
                    frame = cv2.imread(self.temp_frame_file.name, cv2.IMREAD_COLOR)
                    if frame is not None:
                        # Verify resolution
                        h, w = frame.shape[:2]
                        if (h, w) != (self.resolution[1], self.resolution[0]):
                            logger.warning(f"Frame resolution: got {(h, w)}, expected {(self.resolution[1], self.resolution[0])}")
                        self.frame_count += 1
                        if save_to_disk:
                            self._save_frame(frame, output_dir)
                        logger.info(f"✓ Frame captured #{self.frame_count}: shape={frame.shape}, dtype={frame.dtype}")
                        return frame
                else:
                    logger.error(f"rpicam-still capture failed: {result.stderr.decode()}")
                    return None
            
            elif self.camera_version == 'picamera2' and PICAMERA2_AVAILABLE:
                # Pi Camera v3 via picamera2
                if not self.is_ready():
                    logger.error("Camera not ready for capture")
                    return None
                frame = self.camera.capture_array()
                self.frame_count += 1
                if save_to_disk:
                    self._save_frame(frame, output_dir)
                logger.info(f"✓ Frame captured #{self.frame_count}: shape={frame.shape}, dtype={frame.dtype}")
                return frame
            
            else:
                # OpenCV fallback
                if not self.is_ready():
                    logger.error("Camera not ready for capture")
                    return None
                ret, frame = self.camera.read()
                if not ret:
                    logger.error("cv2.VideoCapture.read() failed")
                    return None
                self.frame_count += 1
                if save_to_disk:
                    self._save_frame(frame, output_dir)
                logger.info(f"✓ Frame captured #{self.frame_count}: shape={frame.shape}, dtype={frame.dtype}")
                return frame
        
        except Exception as e:
            logger.error(f"Frame capture failed: {e}")
            return None
    
    def capture_multiple_frames(self, num_frames: int = 3, save_to_disk: bool = True, 
                                output_dir: Optional[str] = None, delay_ms: int = 500) -> list:
        """
        Capture multiple frames with optional delay between captures.
        
        TASK 1.1.1: Used to verify camera focus and consistency across frames
        
        Args:
            num_frames (int): Number of frames to capture
            save_to_disk (bool): Save all captured frames to disk
            output_dir (str): Output directory for frames
            delay_ms (int): Delay (milliseconds) between captures
        
        Returns:
            list: List of captured frames (np.ndarray), or empty list if capture fails
        """
        frames = []
        
        for i in range(num_frames):
            frame = self.capture_frame(save_to_disk=save_to_disk, output_dir=output_dir)
            if frame is not None:
                frames.append(frame)
                if i < num_frames - 1:
                    # Wait before next capture
                    cv2.waitKey(delay_ms)
        
        if len(frames) == num_frames:
            logger.info(f"✓ Successfully captured {num_frames} frames")
        else:
            logger.warning(f"Only captured {len(frames)}/{num_frames} frames")
        
        return frames
    
    def _save_frame(self, frame: np.ndarray, output_dir: Optional[str] = None):
        """Save frame to disk with timestamp filename."""
        if output_dir is None:
            output_dir = "ocr_frames"
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]  # millisecond precision
        filename = f"frame_{timestamp}.jpg"
        filepath = output_path / filename
        
        try:
            cv2.imwrite(str(filepath), frame)
            logger.info(f"✓ Frame saved: {filepath}")
        except Exception as e:
            logger.error(f"Failed to save frame: {e}")
    
    def get_frame_info(self, frame: np.ndarray) -> Dict[str, Any]:
        """
        Extract metadata about a frame.
        
        Returns:
            Dict with keys: shape, dtype, channels, height, width, size_mb
        """
        if frame is None:
            return {}
        
        return {
            "shape": frame.shape,
            "dtype": str(frame.dtype),
            "channels": frame.shape[2] if len(frame.shape) == 3 else 1,
            "height": frame.shape[0],
            "width": frame.shape[1],
            "size_mb": frame.nbytes / (1024 * 1024)
        }
    
    def release(self):
        """Release camera resource."""
        if self.camera is not None:
            try:
                if self.camera_version == 'picamera2' and PICAMERA2_AVAILABLE:
                    self.camera.stop()
                else:
                    self.camera.release()
                logger.info("Camera released")
            except Exception as e:
                logger.error(f"Error releasing camera: {e}")
            finally:
                self.camera = None
        
        # Clean up temporary frame file
        if self.temp_frame_file is not None:
            try:
                os.unlink(self.temp_frame_file.name)
                logger.info(f"Cleaned up temp file: {self.temp_frame_file.name}")
            except Exception as e:
                logger.warning(f"Could not delete temp file: {e}")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.release()


def validate_registration_format(text: str) -> bool:
    """
    Validate UDSM registration number format: 20xx-04-xxxxx
    
    TASK 1.4.1: Regex validator (prepared early for Task 1.1 testing)
    
    Args:
        text (str): Text to validate
    
    Returns:
        bool: True if matches format, False otherwise
        
    Valid examples:
        - 2022-04-09050
        - 2023-04-12345
        - 2024-04-00001
    
    Invalid examples:
        - 2022-05-09050 (wrong fixed segment)
        - 22-04-09050 (wrong year format)
        - 2022-04-9050 (too few digits)
    """
    import re
    pattern = r"^20\d{2}-04-\d{5}$"
    return bool(re.match(pattern, text.strip()))


# ============================================================================
# Configuration constants (can also be moved to config.py)
# ============================================================================

# TASK 1.1.2: Capture workflow configuration
# Import from config.py to keep settings centralized
try:
    from config import (
        OCR_FRAME_RESOLUTION, OCR_FRAME_RATE, OCR_ROI_COORDINATES,
        OCR_TESSERACT_PSM, OCR_TESSERACT_CHAR_WHITELIST, OCR_TESSERACT_MIN_CONFIDENCE,
        OCR_REGISTRATION_FORMAT_REGEX
    )
except ImportError:
    # Fallback defaults if config not available
    OCR_FRAME_RESOLUTION = (2560, 1440)
    OCR_FRAME_RATE = 30
    OCR_ROI_COORDINATES = None
    OCR_TESSERACT_PSM = 7
    OCR_TESSERACT_CHAR_WHITELIST = "0123456789-"
    OCR_TESSERACT_MIN_CONFIDENCE = 0.85
    OCR_REGISTRATION_FORMAT_REGEX = r"^20\d{2}-04-\d{5}$"
TESSERACT_CHAR_WHITELIST = "0123456789-"  # Only digits and hyphen

# TASK 1.4.2: OCR decision logic thresholds
OCR_MIN_CONFIDENCE_THRESHOLD = 0.85  # Confidence threshold for ACCEPT decision
OCR_FORMAT_REGEX = r"^20\d{2}-04-\d{5}$"  # Registration number format

# TASK 1.1.4: ROI (Region of Interest) calibration
# NOTE: These are placeholder values. Will be calibrated in Task 1.1.4 after capture test.
#       Format: (x1, y1, x2, y2) - pixel coordinates of bounding box for registration number
OCR_ROI_COORDINATES = None  # To be calibrated after first capture


# ============================================================================
# Placeholder functions (will be implemented in Tasks 1.2–1.4)
# ============================================================================

def preprocess_frame(frame: np.ndarray, roi_coordinates: Optional[Tuple[int, int, int, int]] = None) -> Tuple[np.ndarray, np.ndarray]:
    """
    Preprocess frame for OCR: grayscale, adaptive threshold, deskew, crop ROI.
    
    TASK 1.2: Image preprocessing pipeline
    
    Args:
        frame (np.ndarray): Input frame (BGR)
        roi_coordinates (Tuple): Optional (x1, y1, x2, y2) for ROI crop
    
    Returns:
        Tuple[np.ndarray, np.ndarray]: (preprocessed_frame, roi_crop)
    """
    # Placeholder: will implement in Task 1.2
    logger.info("preprocess_frame() - PLACEHOLDER (Task 1.2)")
    return frame, frame


def extract_registration_number(frame: np.ndarray, min_confidence: float = OCR_MIN_CONFIDENCE_THRESHOLD) -> Dict[str, Any]:
    """
    Extract registration number from preprocessed frame using Tesseract.
    
    TASK 1.3: Tesseract OCR integration
    
    Args:
        frame (np.ndarray): Preprocessed frame (ideally ROI crop)
        min_confidence (float): Confidence threshold
    
    Returns:
        Dict with keys: success, registration_number, confidence, error
    """
    # Placeholder: will implement in Task 1.3
    logger.info("extract_registration_number() - PLACEHOLDER (Task 1.3)")
    return {
        "success": False,
        "registration_number": None,
        "confidence": 0.0,
        "error": "Not yet implemented (Task 1.3)"
    }
