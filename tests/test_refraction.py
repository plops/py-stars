"""Tests for atmospheric refraction calculations."""

import pytest

from py_stars.refraction import (
    apply_refraction_to_radec,
    atmospheric_refraction_arcmin,
    barometric_pressure_hpa,
)


class TestAtmosphericRefraction:
    """Tests for Bennett atmospheric refraction formula."""

    def test_barometric_pressure_sea_level(self):
        p0 = barometric_pressure_hpa(0.0)
        assert p0 == pytest.approx(1013.25, abs=0.1)

    def test_barometric_pressure_drops_with_altitude(self):
        p_high = barometric_pressure_hpa(2000.0)
        assert p_high < 1013.25
        assert p_high > 700.0

    def test_refraction_near_horizon_is_significant(self):
        # Near horizon (0°), refraction is ~34 arcminutes (~0.5°)
        r_0 = atmospheric_refraction_arcmin(0.0)
        assert 30.0 < r_0 < 40.0

    def test_refraction_decreases_with_elevation(self):
        r_10 = atmospheric_refraction_arcmin(10.0)
        r_45 = atmospheric_refraction_arcmin(45.0)
        r_90 = atmospheric_refraction_arcmin(90.0)

        assert r_10 > r_45 > r_90
        assert r_90 == pytest.approx(0.0, abs=0.01)

    def test_apply_refraction_shifts_star_upward(self):
        lat = 47.0
        lon = 9.0
        gmst = 0.0
        # A star near horizon
        app_ra, app_dec, true_alt, app_alt, r_arcsec = apply_refraction_to_radec(
            ra_deg=100.0,
            dec_deg=20.0,
            lat_deg=lat,
            lon_deg=lon,
            gmst_deg=gmst,
        )

        assert app_alt >= true_alt
        assert r_arcsec >= 0.0
