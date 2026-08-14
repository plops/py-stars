"""Detect stars in grayscale images using tetra3rs centroid extraction.

tetra3rs provides a high-quality centroid extractor that handles background
estimation, thresholding, and sub-pixel centroiding internally. We also
provide ROI / sky cropping and OpenCV-based preprocessing as an alternative approach.
"""

from dataclasses import dataclass, field
from typing import Any

import cv2
import numpy as np
import tetra3rs


@dataclass
class ExtractionResultWrapper:
    """Container for star extraction results when using ROI sub-windows."""

    centroids: list[Any] = field(default_factory=list)
    background_mean: float = 0.0
    background_sigma: float = 0.0
    threshold: float = 0.0
    image_width: int = 0
    image_height: int = 0
    num_blobs_raw: int = 0


def preprocess_image(gray: np.ndarray, blur_sigma: float = 1.0) -> np.ndarray:
    """Preprocess a grayscale image for star detection.

    Applies Gaussian blur for noise reduction and CLAHE for contrast enhancement.

    Args:
        gray: 2D numpy array (uint8 or float64).
        blur_sigma: Sigma for Gaussian blur. 0 = no blur.

    Returns:
        Preprocessed image as uint8.
    """
    if gray.dtype == np.float64:
        img = (gray * 255).astype(np.uint8)
    else:
        img = gray.copy()

    if blur_sigma > 0:
        ksize = int(blur_sigma * 6) | 1
        img = cv2.GaussianBlur(img, (ksize, ksize), blur_sigma)

    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    img = clahe.apply(img)

    return img


def extract_centroids_tetra3(
    gray: np.ndarray,
    sigma_threshold: float = 10.0,
    max_centroids: int | None = 100,
    roi: tuple[int, int, int, int] | None = None,
) -> tetra3rs.ExtractionResult:
    """Extract star centroids using tetra3rs built-in extractor.

    Supports optional Region of Interest (ROI) cropping (e.g. to exclude landscape/ground lights)
    while mapping centroid coordinates back to the full image frame.

    Args:
        gray: 2D numpy array of pixel values.
        sigma_threshold: Detection threshold in sigma above background. Default 10.0.
        max_centroids: Maximum number of centroids to return (brightest first). Default 100.
        roi: Optional (ymin, ymax, xmin, xmax) pixel bounds within gray.

    Returns:
        tetra3rs.ExtractionResult with .centroids list and image statistics.
    """
    full_h, full_w = gray.shape[:2]

    if roi is not None:
        ymin, ymax, xmin, xmax = roi
        ymin = max(0, min(full_h, ymin))
        ymax = max(ymin + 1, min(full_h, ymax))
        xmin = max(0, min(full_w, xmin))
        xmax = max(xmin + 1, min(full_w, xmax))
        sub_img = gray[ymin:ymax, xmin:xmax]
    else:
        ymin, ymax, xmin, xmax = 0, full_h, 0, full_w
        sub_img = gray

    if sub_img.dtype == np.float64:
        image = sub_img.astype(np.float32)
    else:
        image = sub_img

    raw_result = tetra3rs.extract_centroids(
        image,
        sigma_threshold=sigma_threshold,
        max_centroids=max_centroids,
    )

    if roi is None:
        return raw_result

    # Adjust centroid coordinates to be relative to FULL image center
    crop_h, crop_w = sub_img.shape[:2]
    adjusted_centroids = []

    for c in raw_result.centroids:
        # c.x, c.y are relative to sub_img center
        px_crop = c.x + crop_w / 2.0
        py_crop = c.y + crop_h / 2.0

        px_full = px_crop + xmin
        py_full = py_crop + ymin

        adj_x = px_full - full_w / 2.0
        adj_y = py_full - full_h / 2.0

        adjusted_centroids.append(tetra3rs.Centroid(x=adj_x, y=adj_y, brightness=c.brightness))

    # Return extraction result with adjusted centroids
    return ExtractionResultWrapper(
        centroids=adjusted_centroids,
        background_mean=raw_result.background_mean,
        background_sigma=raw_result.background_sigma,
        threshold=raw_result.threshold,
        image_width=full_w,
        image_height=full_h,
        num_blobs_raw=getattr(raw_result, "num_blobs_raw", len(adjusted_centroids)),
    )


def centroids_to_array(centroids: list[Any]) -> np.ndarray:
    """Convert tetra3rs Centroid list to numpy array.

    Args:
        centroids: List of tetra3rs.Centroid objects.

    Returns:
        Array of shape (N, 3) with columns [x, y, brightness].
        x, y are relative to image center.
    """
    if not centroids:
        return np.empty((0, 3))

    return np.array(
        [[c.x, c.y, c.brightness] for c in centroids],
        dtype=np.float64,
    )


def detect_stars_opencv(
    gray: np.ndarray,
    min_threshold: int = 10,
    max_threshold: int = 200,
    min_area: int = 3,
    max_area: int = 500,
) -> list[dict[str, Any]]:
    """Detect stars using OpenCV SimpleBlobDetector.

    Args:
        gray: 2D uint8 numpy array.
        min_threshold: Minimum intensity threshold.
        max_threshold: Maximum intensity threshold.
        min_area: Minimum blob area in pixels.
        max_area: Maximum blob area in pixels.

    Returns:
        List of dicts with keys: x, y, size.
    """
    if gray.dtype != np.uint8:
        if gray.max() <= 1.0:
            gray = (gray * 255).astype(np.uint8)
        else:
            gray = gray.astype(np.uint8)

    inverted = cv2.bitwise_not(gray)

    params = cv2.SimpleBlobDetector.Params()
    params.minThreshold = min_threshold
    params.maxThreshold = max_threshold
    params.filterByArea = True
    params.minArea = min_area
    params.maxArea = max_area
    params.filterByCircularity = True
    params.minCircularity = 0.5
    params.filterByConvexity = False
    params.filterByInertia = False

    detector = cv2.SimpleBlobDetector.create(params)
    keypoints = detector.detect(inverted)

    stars = []
    for kp in keypoints:
        stars.append(
            {
                "x": kp.pt[0],
                "y": kp.pt[1],
                "size": kp.size,
            }
        )

    return stars
