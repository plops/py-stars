"""Tests for astrometric coordinate transformations and sidereal time."""

from datetime import datetime, timezone

import pytest

from py_stars.astrometry import (
    altaz_to_radec,
    gmst_to_lst_deg,
    radec_to_altaz,
    utc_to_gmst_deg,
)


class TestSiderealTime:
    """Tests for GMST and LST calculations."""

    def test_utc_to_gmst_range(self):
        dt = datetime(2026, 8, 14, 22, 0, 0, tzinfo=timezone.utc)
        gmst = utc_to_gmst_deg(dt)
        assert 0.0 <= gmst < 360.0

    def test_gmst_to_lst(self):
        gmst = 100.0
        lon = 10.0
        lst = gmst_to_lst_deg(gmst, lon)
        assert lst == pytest.approx(110.0)

    def test_gmst_wraparound(self):
        gmst = 355.0
        lon = 10.0
        lst = gmst_to_lst_deg(gmst, lon)
        assert lst == pytest.approx(5.0)


class TestCoordinateTransform:
    """Tests for RA/Dec to Alt/Az and round-trip conversion."""

    def test_radec_to_altaz_zenith(self):
        # A star directly overhead: Dec = lat, RA = LST
        lat = 45.0
        lon = 10.0
        gmst = 50.0
        lst = (gmst + lon) % 360.0  # 60.0

        alt, az = radec_to_altaz(ra_deg=lst, dec_deg=lat, lat_deg=lat, lon_deg=lon, gmst_deg=gmst)
        assert alt == pytest.approx(90.0, abs=1e-3)

    def test_altaz_to_radec_roundtrip(self):
        lat = 47.4
        lon = 9.6
        gmst = 120.0

        original_ra = 150.0
        original_dec = 35.0

        alt, az = radec_to_altaz(original_ra, original_dec, lat, lon, gmst)
        reconstructed_ra, reconstructed_dec = altaz_to_radec(alt, az, lat, lon, gmst)

        assert reconstructed_ra == pytest.approx(original_ra, abs=1e-4)
        assert reconstructed_dec == pytest.approx(original_dec, abs=1e-4)
