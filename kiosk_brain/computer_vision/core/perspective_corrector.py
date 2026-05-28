"""
Perspective correction module for Registration Card system.

Converts a detected card (4 corners) into a top-down, straightened view
with a standardized size.
"""

from typing import Tuple
import cv2
import numpy as np

from config.ocr_config import CARD_OUTPUT_SIZE


def order_points(pts: np.ndarray) -> np.ndarray:
    """
    Order points in consistent order: top-left, top-right, bottom-right, bottom-left.

    Args:
        pts: Array of 4 points, shape (4, 2)

    Returns:
        Ordered array of 4 points
    """
    ordered = np.zeros((4, 2), dtype=np.float32)
    s = pts.sum(axis=1)
    diff = np.diff(pts, axis=1)

    ordered[0] = pts[np.argmin(s)]  # top-left
    ordered[2] = pts[np.argmax(s)]  # bottom-right
    ordered[1] = pts[np.argmin(diff)]  # top-right
    ordered[3] = pts[np.argmax(diff)]  # bottom-left

    return ordered


def straighten_card(image: np.ndarray, corners: np.ndarray) -> np.ndarray:
    """
    Apply perspective transform to get a top-down view of the card.

    Args:
        image: Original image (BGR)
        corners: 4 corner points of the card

    Returns:
        Straightened card image with standardized size
    """
    if image is None or image.size == 0:
        raise ValueError("Invalid input image")

    if corners is None or len(corners) != 4:
        raise ValueError("Invalid corners: must provide 4 corner points")

    # Ensure correct order of corners
    rect = order_points(corners)

    # Destination points (standardized size)
    width, height = CARD_OUTPUT_SIZE
    dst = np.array(
        [[0, 0], [width - 1, 0], [width - 1, height - 1], [0, height - 1]],
        dtype=np.float32,
    )

    # Compute perspective transform matrix
    matrix = cv2.getPerspectiveTransform(rect, dst)

    # Apply warp perspective
    warped = cv2.warpPerspective(image, matrix, (width, height))

    return warped


def get_perspective_transform(
    image: np.ndarray, corners: np.ndarray
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Get the perspective transform matrix and warped image.

    Args:
        image: Original image (BGR)
        corners: 4 corner points of the card

    Returns:
        (matrix, warped_image)
    """
    if image is None or image.size == 0:
        raise ValueError("Invalid input image")

    if corners is None or len(corners) != 4:
        raise ValueError("Invalid corners: must provide 4 corner points")

    rect = order_points(corners)
    width, height = CARD_OUTPUT_SIZE

    dst = np.array(
        [[0, 0], [width - 1, 0], [width - 1, height - 1], [0, height - 1]],
        dtype=np.float32,
    )

    matrix = cv2.getPerspectiveTransform(rect, dst)

    warped = cv2.warpPerspective(image, matrix, (width, height))

    return matrix, warped
