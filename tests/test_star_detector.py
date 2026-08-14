"""Tests for star detection."""

import numpy as np
import tetra3rs

from py_stars.star_detector import (
    centroids_to_array,
    detect_stars_opencv,
    extract_centroids_tetra3,
    preprocess_image,
)


def make_synthetic_star_image(width: int = 200, height: int = 200, n_stars: int = 5) -> np.ndarray:
    """Create a synthetic image with bright dots on dark background."""
    rng = np.random.default_rng(42)
    img = np.zeros((height, width), dtype=np.uint8)
    # Add some background noise
    img = img + rng.integers(5, 15, size=(height, width), dtype=np.uint8)
    # Add bright stars at random positions (away from edges)
    for _ in range(n_stars):
        x = rng.integers(20, width - 20)
        y = rng.integers(20, height - 20)
        # Draw a small bright spot (3x3)
        for dx in range(-1, 2):
            for dy in range(-1, 2):
                brightness = 200 if (dx == 0 and dy == 0) else 120
                img[y + dy, x + dx] = min(255, img[y + dy, x + dx] + brightness)
    return img


class TestPreprocessImage:
    """Tests for image preprocessing."""

    def test_preserves_shape(self):
        img = np.zeros((100, 100), dtype=np.uint8)
        result = preprocess_image(img)
        assert result.shape == img.shape

    def test_returns_uint8(self):
        img = np.zeros((100, 100), dtype=np.uint8)
        result = preprocess_image(img)
        assert result.dtype == np.uint8

    def test_accepts_float64(self):
        img = np.zeros((100, 100), dtype=np.float64)
        result = preprocess_image(img)
        assert result.dtype == np.uint8


class TestExtractCentroidsTetra3:
    """Tests for tetra3rs centroid extraction."""

    def test_returns_extraction_result(self):
        img = make_synthetic_star_image()
        result = extract_centroids_tetra3(img)
        assert isinstance(result, tetra3rs.ExtractionResult)

    def test_finds_centroids_in_synthetic_image(self):
        img = make_synthetic_star_image(n_stars=5)
        result = extract_centroids_tetra3(img, sigma_threshold=3.0)
        assert len(result.centroids) >= 1  # should find at least some stars

    def test_empty_image_finds_nothing(self):
        img = np.zeros((100, 100), dtype=np.uint8)
        result = extract_centroids_tetra3(img)
        assert len(result.centroids) == 0


class TestCentroidsToArray:
    """Tests for centroid conversion."""

    def test_empty_list_returns_empty_array(self):
        arr = centroids_to_array([])
        assert arr.shape == (0, 3)

    def test_converts_centroids(self):
        centroids = [tetra3rs.Centroid(1.0, 2.0, brightness=100.0)]
        arr = centroids_to_array(centroids)
        assert arr.shape == (1, 3)
        assert arr[0, 0] == 1.0
        assert arr[0, 1] == 2.0


class TestDetectStarsOpencv:
    """Tests for OpenCV blob detection."""

    def test_returns_list(self):
        img = make_synthetic_star_image()
        stars = detect_stars_opencv(img)
        assert isinstance(stars, list)

    def test_star_dicts_have_required_keys(self):
        img = make_synthetic_star_image(n_stars=10)
        stars = detect_stars_opencv(img, min_threshold=5, min_area=2)
        if len(stars) > 0:
            for key in ["x", "y", "size"]:
                assert key in stars[0]
