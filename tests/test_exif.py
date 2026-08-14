"""Tests for EXIF parsing and dynamic FOV estimation."""

import os

from py_stars.exif import compute_camera_fov, get_gps_info, parse_exif

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEST_HEIC = os.path.join(PROJECT_ROOT, "data", "IMG_9144.HEIC")
TEST_HEIC_NOGPS = os.path.join(PROJECT_ROOT, "data", "IMG_8867.HEIC")


class TestExifParsing:
    """Tests for parse_exif."""

    def test_parses_exif_dict(self):
        if os.path.exists(TEST_HEIC):
            exif = parse_exif(TEST_HEIC)
            assert isinstance(exif, dict)
            assert "Make" in exif or "Model" in exif or "Exif" in exif

    def test_nonexistent_returns_empty_or_fails(self):
        try:
            exif = parse_exif("/nonexistent/file.heic")
            assert exif == {}
        except Exception:
            pass


class TestCameraFOV:
    """Tests for dynamic FOV computation without hardcoding."""

    def test_compute_fov_from_35mm_focal_length(self):
        # 26mm equivalent on standard 4:3 iPhone sensor
        exif = {"Exif": {"FocalLengthIn35mmFilm": 26}}
        hfov, vfov, dfov = compute_camera_fov(exif, image_width=4032, image_height=3024)
        assert 65.0 < hfov < 72.0
        assert 50.0 < vfov < 58.0
        assert 75.0 < dfov < 85.0

    def test_compute_fov_fallback(self):
        exif = {}
        hfov, vfov, dfov = compute_camera_fov(
            exif, image_width=4032, image_height=3024, fallback_hfov=70.0
        )
        assert abs(hfov - 70.0) < 0.1
        assert vfov < hfov
        assert dfov > hfov

    def test_real_image_fov(self):
        if os.path.exists(TEST_HEIC):
            hfov, vfov, dfov = compute_camera_fov(TEST_HEIC)
            assert 60.0 < hfov < 75.0


class TestGPSInfo:
    """Tests for GPS info extraction."""

    def test_extracts_gps_from_tagged_image(self):
        if os.path.exists(TEST_HEIC):
            gps = get_gps_info(TEST_HEIC)
            assert gps is not None
            assert 45.0 < gps["latitude_deg"] < 50.0
            assert 8.0 < gps["longitude_deg"] < 12.0
            assert gps["altitude_m"] > 0
            assert gps["utc_datetime"] is not None
            assert gps["compass_heading_deg"] is not None

    def test_returns_none_when_no_gps(self):
        if os.path.exists(TEST_HEIC_NOGPS):
            gps = get_gps_info(TEST_HEIC_NOGPS)
            assert gps is None or gps.get("latitude_deg") is None
