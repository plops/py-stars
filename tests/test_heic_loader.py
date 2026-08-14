"""Tests for HEIC image loading."""

import numpy as np
import pytest
from PIL import Image

from py_stars.heic_loader import (
    get_image_info,
    load_heic,
    load_heic_as_gray,
    load_heic_as_uint8,
)

# Real HEIC file for integration tests
TEST_HEIC_FILE = "/workspace/src/IMG_8556.HEIC"


class TestLoadHeic:
    """Tests for load_heic function."""

    def test_loads_as_pil_image(self):
        img = load_heic(TEST_HEIC_FILE)
        assert isinstance(img, Image.Image)

    def test_returns_rgb_mode(self):
        img = load_heic(TEST_HEIC_FILE)
        assert img.mode == "RGB"

    def test_has_positive_dimensions(self):
        img = load_heic(TEST_HEIC_FILE)
        assert img.width > 0
        assert img.height > 0

    def test_raises_on_missing_file(self):
        with pytest.raises(FileNotFoundError):
            load_heic("/nonexistent/path/to/file.heic")


class TestLoadHeicAsGray:
    """Tests for load_heic_as_gray function."""

    def test_returns_numpy_array(self):
        gray = load_heic_as_gray(TEST_HEIC_FILE)
        assert isinstance(gray, np.ndarray)

    def test_is_2d(self):
        gray = load_heic_as_gray(TEST_HEIC_FILE)
        assert gray.ndim == 2

    def test_is_float64(self):
        gray = load_heic_as_gray(TEST_HEIC_FILE)
        assert gray.dtype == np.float64

    def test_values_normalized_0_to_1(self):
        gray = load_heic_as_gray(TEST_HEIC_FILE)
        assert gray.min() >= 0.0
        assert gray.max() <= 1.0


class TestLoadHeicAsUint8:
    """Tests for load_heic_as_uint8 function."""

    def test_returns_uint8(self):
        gray = load_heic_as_uint8(TEST_HEIC_FILE)
        assert gray.dtype == np.uint8

    def test_is_2d(self):
        gray = load_heic_as_uint8(TEST_HEIC_FILE)
        assert gray.ndim == 2


class TestGetImageInfo:
    """Tests for get_image_info function."""

    def test_returns_dict(self):
        info = get_image_info(TEST_HEIC_FILE)
        assert isinstance(info, dict)

    def test_has_required_keys(self):
        info = get_image_info(TEST_HEIC_FILE)
        for key in ["width", "height", "mode", "format"]:
            assert key in info

    def test_dimensions_are_positive(self):
        info = get_image_info(TEST_HEIC_FILE)
        assert info["width"] > 0
        assert info["height"] > 0
