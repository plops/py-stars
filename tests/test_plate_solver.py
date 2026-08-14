"""Tests for plate solving."""

from py_stars.plate_solver import (
    IPHONE11_HFOV,
    IPHONE11_VFOV,
    _deg_to_dms,
    _deg_to_hms,
    format_result,
)


class TestConstants:
    """Tests for camera constants."""

    def test_iphone11_hfov_reasonable(self):
        assert 60 < IPHONE11_HFOV < 90

    def test_iphone11_vfov_reasonable(self):
        assert 40 < IPHONE11_VFOV < 70


class TestCoordinateFormatting:
    """Tests for coordinate formatting helpers."""

    def test_deg_to_hms_zero(self):
        result = _deg_to_hms(0.0)
        assert "00h" in result

    def test_deg_to_hms_180(self):
        result = _deg_to_hms(180.0)
        assert "12h" in result

    def test_deg_to_dms_positive(self):
        result = _deg_to_dms(45.5)
        assert "+" in result
        assert "45" in result

    def test_deg_to_dms_negative(self):
        result = _deg_to_dms(-30.0)
        assert "-" in result
        assert "30" in result


class TestFormatResult:
    """Tests for result formatting."""

    def test_format_failure(self):
        # Create a mock SolveFailure-like object
        class MockFailure:
            def __bool__(self):
                return False

            status = "no_match"
            solve_time_ms = 100.0

        text = format_result(MockFailure())
        assert "FAILED" in text
        assert "no_match" in text
