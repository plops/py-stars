"""Unit tests for SGP4 satellite orbit propagation, TLE handling, and streak matching."""

from dataclasses import dataclass
from datetime import datetime, timezone

from py_stars.ephemeris import get_ephemeris_context
from py_stars.satellites import (
    match_satellites_with_centroids,
    parse_tle_data,
    propagate_satellite_trajectory,
    query_satellites_in_fov,
)

SAMPLE_TLE_3LINE = """ISS (ZARYA)
1 25544U 98067A   24227.54583333  .00016717  00000+0  30000-3 0  9993
2 25544  51.6416 180.1234 0004567  85.1234 275.1234 15.49876543456789
TIANGONG
1 48274U 21035A   24227.50000000  .00021543  00000+0  25000-3 0  9991
2 48274  41.4721 165.3421 0005123 110.2312 250.1234 15.60123456182345
"""

SAMPLE_TLE_2LINE = """1 25544U 98067A   24227.54583333  .00016717  00000+0  30000-3 0  9993
2 25544  51.6416 180.1234 0004567  85.1234 275.1234 15.49876543456789
"""


@dataclass
class MockCentroid:
    x: float  # Center-origin X [-W/2, +W/2]
    y: float  # Center-origin Y [-H/2, +H/2]
    brightness: float = 5000.0


class MockSolveResult:
    """Mock SolveResult for testing satellite FOV projections."""

    def __init__(self, ra_deg: float = 107.3, dec_deg: float = -51.2, fov_deg: float = 70.0):
        self.ra_deg = ra_deg
        self.dec_deg = dec_deg
        self.fov_deg = fov_deg

    def world_to_pixel(self, ra: float, dec: float) -> tuple[float, float]:
        px = (ra - self.ra_deg) * 30.0
        py = (dec - self.dec_deg) * 30.0
        return px, py


class TestSatelliteOrbitPropagation:
    """Test suite for SGP4 orbit propagation and TLE parsing."""

    def test_parse_3line_tle(self) -> None:
        """Verify parsing 3-line TLE format."""
        _, ts, _ = get_ephemeris_context()
        sats = parse_tle_data(SAMPLE_TLE_3LINE, ts=ts)
        assert len(sats) == 2
        assert sats[0].name == "ISS (ZARYA)"
        assert sats[1].name == "TIANGONG"

    def test_parse_2line_tle(self) -> None:
        """Verify parsing 2-line TLE format."""
        _, ts, _ = get_ephemeris_context()
        sats = parse_tle_data(SAMPLE_TLE_2LINE, ts=ts)
        assert len(sats) == 1
        assert "25544" in sats[0].name

    def test_propagate_satellite_trajectory(self) -> None:
        """Test propagating satellite coordinates and waypoints over an exposure time."""
        _, ts, eph = get_ephemeris_context()
        sats = parse_tle_data(SAMPLE_TLE_3LINE, ts=ts)
        iss = sats[0]

        dt = datetime(2024, 8, 14, 22, 0, 0, tzinfo=timezone.utc)
        lat, lon, alt_m = 48.137, 11.576, 520.0

        pass_res = propagate_satellite_trajectory(
            satellite=iss,
            lat_deg=lat,
            lon_deg=lon,
            alt_m=alt_m,
            utc_dt=dt,
            exposure_seconds=3.0,
            num_steps=5,
            ephemeris=eph,
            ts=ts,
        )

        assert pass_res is not None
        assert pass_res.name == "ISS (ZARYA)"
        assert pass_res.norad_cat_id == 25544
        assert len(pass_res.waypoints) == 5
        assert pass_res.mid_range_km > 300.0  # Above Earth surface

    def test_query_satellites_in_fov(self) -> None:
        """Test FOV filtering of satellites."""
        _, ts, eph = get_ephemeris_context()
        sats = parse_tle_data(SAMPLE_TLE_3LINE, ts=ts)
        dt = datetime(2024, 8, 14, 22, 0, 0, tzinfo=timezone.utc)

        # Propagate first to see where ISS is
        test_pass = propagate_satellite_trajectory(
            sats[0], lat_deg=48.0, lon_deg=11.0, alt_m=0.0, utc_dt=dt, ts=ts
        )
        assert test_pass is not None

        # Create mock solve centered on ISS coordinates
        solve = MockSolveResult(ra_deg=test_pass.mid_ra_deg, dec_deg=test_pass.mid_dec_deg)

        res = query_satellites_in_fov(
            satellites=sats,
            lat_deg=48.0,
            lon_deg=11.0,
            alt_m=0.0,
            utc_dt=dt,
            solve_result=solve,
            image_width=4032,
            image_height=3024,
            exposure_seconds=2.0,
            min_altitude_deg=-90.0,  # Include below horizon for test
            ephemeris=eph,
            ts=ts,
        )

        assert res.in_fov_count >= 1
        assert res.passes[0].is_in_fov is True
        assert res.passes[0].streak_length_px >= 0.0

    def test_match_satellites_with_centroids(self) -> None:
        """Test matching satellite streak/point with image centroids."""
        _, ts, eph = get_ephemeris_context()
        sats = parse_tle_data(SAMPLE_TLE_3LINE, ts=ts)
        dt = datetime(2024, 8, 14, 22, 0, 0, tzinfo=timezone.utc)

        test_pass = propagate_satellite_trajectory(
            sats[0], lat_deg=48.0, lon_deg=11.0, alt_m=0.0, utc_dt=dt, ts=ts
        )
        assert test_pass is not None
        solve = MockSolveResult(ra_deg=test_pass.mid_ra_deg, dec_deg=test_pass.mid_dec_deg)

        pass_fov = propagate_satellite_trajectory(
            sats[0],
            lat_deg=48.0,
            lon_deg=11.0,
            alt_m=0.0,
            utc_dt=dt,
            solve_result=solve,
            image_width=4032,
            image_height=3024,
            exposure_seconds=2.0,
            ts=ts,
        )
        assert pass_fov is not None

        # Place a mock centroid near the satellite waypoint
        wp = pass_fov.waypoints[0]
        # Top-left is wp.image_x, center-origin is wp.px
        centroids = [
            MockCentroid(x=wp.px + 1.0, y=wp.py - 1.0, brightness=10000.0),
            MockCentroid(x=-1500.0, y=-1000.0, brightness=2000.0),  # Far away
        ]

        matches = match_satellites_with_centroids(
            satellite_passes=[pass_fov],
            centroids=centroids,
            image_width=4032,
            image_height=3024,
            solve_result=solve,
            max_match_radius_px=15.0,
        )

        assert len(matches) == 1
        assert matches[0].centroid_idx == 0
        assert matches[0].min_distance_px < 2.0
