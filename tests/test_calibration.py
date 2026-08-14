"""Tests for camera distortion calibration module."""

import os

from py_stars.calibration import (
    DEFAULT_POLY_MODEL_PATH,
    DEFAULT_RADIAL_MODEL_PATH,
    get_default_camera_model,
    load_camera_model,
)


class TestCameraCalibration:
    """Tests for loading and using calibrated camera models."""

    def test_load_default_radial_model_if_exists(self):
        if os.path.exists(DEFAULT_RADIAL_MODEL_PATH):
            model = load_camera_model(DEFAULT_RADIAL_MODEL_PATH)
            assert model is not None
            assert model.focal_length_px > 1000
            assert model.distortion is not None

    def test_get_default_camera_model(self):
        model = get_default_camera_model("radial")
        if os.path.exists(DEFAULT_RADIAL_MODEL_PATH):
            assert model is not None

    def test_load_default_poly_model_if_exists(self):
        if os.path.exists(DEFAULT_POLY_MODEL_PATH):
            model = load_camera_model(DEFAULT_POLY_MODEL_PATH)
            assert model is not None
            assert model.distortion is not None
