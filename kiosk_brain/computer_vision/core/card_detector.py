"""
Card Detection Module for Registration Card System

This module detects ID cards in images and returns their corner coordinates.
Uses OpenCV contour detection with filtering based on card properties.
"""

import cv2
import numpy as np
from typing import Optional, Tuple
import sys
from pathlib import Path

# Add parent directory to path for config import
sys.path.append(str(Path(__file__).parent.parent))
from config.ocr_config import CARD_DETECTION, CARD_PHYSICAL
from core.exceptions import CardNotFoundError, CardDetectionAmbiguousError


def detect_card(image: np.ndarray, debug: bool = False) -> Optional[np.ndarray]:
    """
    Detect ID card in image and return corner coordinates.

    Args:
        image: Input image (BGR format from cv2.imread)
        debug: If True, return intermediate processing images

    Returns:
        Array of 4 corner points ordered as:
        [top-left, top-right, bottom-right, bottom-left]
        Each point is (x, y) coordinates
        Returns None if no card detected

    Raises:
        CardNotFoundError: No card-like contour found
        CardDetectionAmbiguousError: Multiple valid cards detected
    """
    if image is None or image.size == 0:
        raise ValueError("Invalid input image: None or empty")

    # Preprocess image for edge detection
    edges = preprocess_for_detection(image)

    # Find contours in edge image
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Filter contours to find card-like shapes
    card_contours = find_card_contours(contours, image.shape)

    if len(card_contours) == 0:
        if debug:
            return None
        raise CardNotFoundError("No card detected in image")

    if len(card_contours) > 1:
        # Multiple valid cards detected - use the largest one
        card_contours.sort(key=cv2.contourArea, reverse=True)
        print(f"Warning: {len(card_contours)} cards detected, using largest")

    # Extract and order corner points
    corners = extract_corners(card_contours[0])

    return corners


def preprocess_for_detection(image: np.ndarray) -> np.ndarray:
    """
    Preprocess image for card edge detection.

    Uses simple edge detection focused on card boundaries.

    Args:
        image: Input BGR image

    Returns:
        Binary edge image
    """
    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Apply Gaussian blur to remove noise
    blurred = cv2.GaussianBlur(gray, (7, 7), 0)

    # Apply Canny edge detection
    edges = cv2.Canny(
        blurred, CARD_DETECTION["canny_threshold1"], CARD_DETECTION["canny_threshold2"]
    )

    # Moderate morphological operations
    kernel = np.ones((5, 5), np.uint8)

    # Dilate to connect close edges
    edges = cv2.dilate(edges, kernel, iterations=2)

    # Close small gaps
    edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel, iterations=1)

    return edges


def find_card_contours(contours: list, image_shape: Tuple[int, int, int]) -> list:
    """
    Filter contours to find card-like rectangular shapes.

    Filtering criteria:
    - Area within valid range (not too small/large)
    - Aspect ratio matches card dimensions (88x55mm ≈ 1.6:1)
    - Has 4 corners (quadrilateral)

    Args:
        contours: List of detected contours
        image_shape: Shape of original image (height, width, channels)

    Returns:
        List of contours that match card properties
    """
    card_contours = []
    image_area = image_shape[0] * image_shape[1]

    for contour in contours:
        # Calculate contour area
        area = cv2.contourArea(contour)

        # Filter by area (card should be significant portion of image)
        min_area = CARD_DETECTION["min_area"]
        max_area = min(CARD_DETECTION["max_area"], image_area * 0.9)

        if area < min_area or area > max_area:
            continue

        # Approximate contour to polygon with MORE aggressive simplification
        # Higher epsilon = simpler polygon with fewer vertices
        peri = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(
            contour, 0.04 * peri, True
        )  # Increased from 0.02 to 0.04

        # Card should be roughly rectangular (4-12 vertices)
        # Accept slightly imperfect shapes due to broken edges
        if len(approx) < 4 or len(approx) > 12:  # Increased from 8 to 12
            continue

        # Calculate bounding rectangle to check aspect ratio
        rect = cv2.minAreaRect(contour)
        width, height = rect[1]

        # Avoid division by zero
        if width == 0 or height == 0:
            continue

        # Calculate aspect ratio (normalize to always be >= 1.0)
        aspect_ratio = max(width, height) / min(width, height)
        expected_ratio = CARD_PHYSICAL["width_mm"] / CARD_PHYSICAL["height_mm"]
        tolerance = CARD_DETECTION["aspect_ratio_tolerance"]

        # Check if aspect ratio matches card dimensions
        if abs(aspect_ratio - expected_ratio) <= tolerance:
            card_contours.append(contour)

    return card_contours


def extract_corners(contour: np.ndarray) -> np.ndarray:
    """
    Extract and order corner points from card contour.

    Corner ordering:
    [0] = top-left
    [1] = top-right
    [2] = bottom-right
    [3] = bottom-left

    Args:
        contour: Card contour

    Returns:
        Array of 4 corner points, shape (4, 2)
    """
    # Use minimum area bounding rectangle for stable corners
    rect = cv2.minAreaRect(contour)
    box = cv2.boxPoints(rect)
    corners = np.array(box, dtype=np.float32).reshape(4, 2)

    # Order corners consistently
    corners = order_points(corners)

    return corners


def order_points(pts: np.ndarray) -> np.ndarray:
    """
    Order points in consistent manner: top-left, top-right, bottom-right, bottom-left.

    Algorithm:
    - Top-left: smallest sum (x + y)
    - Bottom-right: largest sum (x + y)
    - Top-right: smallest difference (y - x)
    - Bottom-left: largest difference (y - x)

    Args:
        pts: Array of 4 points, shape (4, 2)

    Returns:
        Ordered array of 4 points
    """
    # Initialize ordered points array
    ordered = np.zeros((4, 2), dtype=np.float32)

    # Sum and difference of coordinates
    s = pts.sum(axis=1)
    diff = np.diff(pts, axis=1)

    # Top-left has smallest sum
    ordered[0] = pts[np.argmin(s)]

    # Bottom-right has largest sum
    ordered[2] = pts[np.argmax(s)]

    # Top-right has smallest difference
    ordered[1] = pts[np.argmin(diff)]

    # Bottom-left has largest difference
    ordered[3] = pts[np.argmax(diff)]

    return ordered


def draw_corners(
    image: np.ndarray, corners: np.ndarray, color: Tuple[int, int, int] = (0, 255, 0)
) -> np.ndarray:
    """
    Draw corner points and card outline on image for visualization.

    Args:
        image: Input image
        corners: Array of 4 corner points
        color: BGR color for drawing (default: green)

    Returns:
        Image with corners and outline drawn
    """
    output = image.copy()

    # Draw corner points (circles)
    for i, corner in enumerate(corners):
        x, y = int(corner[0]), int(corner[1])
        cv2.circle(output, (x, y), 10, color, -1)  # Filled circle
        # Add corner label
        cv2.putText(
            output, str(i), (x + 15, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2
        )

    # Draw card outline (lines connecting corners)
    corners_int = corners.astype(np.int32)
    cv2.polylines(output, [corners_int], True, color, 3)

    return output


def get_card_info(corners: np.ndarray) -> dict:
    """
    Calculate card properties from corner points.

    Args:
        corners: Array of 4 corner points

    Returns:
        Dictionary with card properties:
        - width: Card width in pixels
        - height: Card height in pixels
        - aspect_ratio: Width/height ratio
        - area: Card area in pixels
        - center: Card center point (x, y)
    """
    # Calculate dimensions
    width_top = np.linalg.norm(corners[0] - corners[1])
    width_bottom = np.linalg.norm(corners[3] - corners[2])
    width = (width_top + width_bottom) / 2

    height_left = np.linalg.norm(corners[0] - corners[3])
    height_right = np.linalg.norm(corners[1] - corners[2])
    height = (height_left + height_right) / 2

    # Calculate center
    center = np.mean(corners, axis=0)

    return {
        "width": width,
        "height": height,
        "aspect_ratio": width / height if height > 0 else 0,
        "area": width * height,
        "center": tuple(center.astype(int)),
    }
