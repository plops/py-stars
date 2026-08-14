"""Unit tests for Solar System ephemeris calculations (Skyfield)."""

from datetime import datetime, timezone

from py_stars.ephemeris import (
    PLANETARY_TARGETS,
    estimate_planet_magnitude,
    get_ephemeris_context,
    query_solar_system_ephemerides,
)


class MockSolveResult:
    """Mock SolveResult for testing planet FOV projections."""

    def __init__(self, ra_deg: float = 75.0, dec_deg: float = 22.0, fov_deg: float = 65.0):
        self.ra_deg = ra_deg
        self.dec_deg = dec_deg
        self.fov_deg = fov_deg

    def world_to_pixel(self, ra: float, dec: float) -> tuple[float, float]:
        px = (ra - self.ra_deg) * 40.0
        py = (dec - self.dec_deg) * 40.0
        return px, py


class TestSolarSystemEphemerides:
    """Test suite for planetary and lunar ephemeris queries."""

    def test_ephemeris_context_loads(self) -> None:
        """Test loader and timescale initialization."""
        loader, ts, eph = get_ephemeris_context()
        assert loader is not None
        assert ts is not None
        assert eph is not None

    def test_query_major_bodies(self) -> None:
        """Test calculation of apparent positions for all major bodies."""
        dt = datetime(2024, 8, 14, 22, 0, 0, tzinfo=timezone.utc)
        lat = 48.137  # Munich, Germany
        lon = 11.576
        alt_m = 520.0

        res = query_solar_system_ephemerides(
            utc_dt=dt,
            lat_deg=lat,
            lon_deg=lon,
            alt_m=alt_m,
        )

        assert res.observer_latitude_deg == lat
        assert res.observer_longitude_deg == lon
        assert len(res.bodies) == len(PLANETARY_TARGETS)

        body_dict = {b.name: b for b in res.bodies}

        # Check Moon
        assert "Moon" in body_dict
        moon = body_dict["Moon"]
        assert 0.0 <= moon.ra_deg < 360.0
        assert -90.0 <= moon.dec_deg <= 90.0
        assert -90.0 <= moon.alt_deg <= 90.0
        assert 0.0 <= moon.az_deg < 360.0
        assert moon.distance_km > 350000.0
        assert moon.angular_diameter_arcsec > 1500.0  # Moon is ~30 arcmin (1800 arcsec)

        # Check Sun
        assert "Sun" in body_dict
        sun = body_dict["Sun"]
        assert sun.distance_au > 0.98

        # Check Jupiter and Mars
        assert "Jupiter" in body_dict
        assert "Mars" in body_dict

    def test_planetary_fov_projection(self) -> None:
        """Test projecting celestial bodies onto a solved camera sensor."""
        dt = datetime(2024, 8, 14, 22, 0, 0, tzinfo=timezone.utc)
        # On 2024-08-14, Jupiter was around RA 75.3°, Dec 22.0°
        solve = MockSolveResult(ra_deg=75.3, dec_deg=22.0, fov_deg=65.0)

        res = query_solar_system_ephemerides(
            utc_dt=dt,
            lat_deg=48.137,
            lon_deg=11.576,
            alt_m=520.0,
            solve_result=solve,
            image_width=4032,
            image_height=3024,
        )

        in_fov_names = [b.name for b in res.bodies_in_fov]
        assert "Jupiter" in in_fov_names or "Mars" in in_fov_names

        for b in res.bodies_in_fov:
            assert b.is_in_fov is True
            assert b.image_x is not None
            assert 0 <= b.image_x <= 4032
            assert 0 <= b.image_y <= 3024

    def test_estimate_magnitude(self) -> None:
        """Test visual magnitude approximations for planets."""
        sun_mag = estimate_planet_magnitude("Sun", 1.0, 1.0, 0.0)
        assert sun_mag == -26.74

        venus_mag = estimate_planet_magnitude("Venus", 0.72, 1.0, 45.0)
        assert venus_mag is not None and -5.0 < venus_mag < -3.0

        jupiter_mag = estimate_planet_magnitude("Jupiter", 5.2, 4.2, 5.0)
        assert jupiter_mag is not None and -3.0 < jupiter_mag < -1.5
