"""Detect stars in grayscale images using tetra3rs centroid extraction.

tetra3rs provides a high-quality centroid extractor that handles background
estimation, thresholding, and sub-pixel centroiding internally. We also
provide OpenCV-based preprocessing as an alternative approach.
"""

import cv2
import numpy as np
import tetra3rs


def preprocess_image(gray: np.ndarray, blur_sigma: float = 1.0) -> np.ndarray:
    """Preprocess a grayscale image for star detection.

    Applies Gaussian blur for noise reduction and CLAHE for contrast enhancement.

    Args:
        gray: 2D numpy array (uint8 or float64).
        blur_sigma: Sigma for Gaussian blur. 0 = no blur.

    Returns:
        Preprocessed image as uint8.
    """
    # Ensure uint8
    if gray.dtype == np.float64:
        img = (gray * 255).astype(np.uint8)
    else:
        img = gray.copy()

    # Gaussian blur for noise reduction
    if blur_sigma > 0:
        ksize = int(blur_sigma * 6) | 1  # ensure odd kernel size
        img = cv2.GaussianBlur(img, (ksize, ksize), blur_sigma)

    # CLAHE for local contrast enhancement
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    img = clahe.apply(img)

    return img


def extract_centroids_tetra3(
    gray: np.ndarray,
    sigma_threshold: float = 10.0,
    max_centroids: int | None = 100,
) -> tetra3rs.ExtractionResult:
    """Extract star centroids using tetra3rs built-in extractor.

    This is the recommended method - tetra3rs handles background estimation,
    thresholding, connected-component labeling, and sub-pixel centroiding.

    Args:
        gray: 2D numpy array of pixel values.
        sigma_threshold: Detection threshold in sigma above background. Default 10.0.
        max_centroids: Maximum number of centroids to return (brightest first). Default 100.

    Returns:
        tetra3rs.ExtractionResult with .centroids list and image statistics.
    """
    # tetra3rs accepts uint8, uint16, float32, float64
    if gray.dtype == np.float64:
        image = gray.astype(np.float32)
    else:
        image = gray

    result = tetra3rs.extract_centroids(
        image,
        sigma_threshold=sigma_threshold,
        max_centroids=max_centroids,
    )
    return result


def centroids_to_array(centroids: list) -> np.ndarray:
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
) -> list[dict]:
    """Detect stars using OpenCV SimpleBlobDetector.

    Alternative approach - useful for comparison or when tetra3rs
    centroid extraction doesn't work well.

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

    # Invert image (blob detector finds dark blobs on light background)
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
