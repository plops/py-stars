"""Satellite orbit propagation (SGP4), TLE fetching, and image matching.

Fetches Two-Line Element (TLE) datasets, propagates orbits for any GPS location and UTC time,
calculates satellite streaks across exposure intervals, and correlates with detected image features.
"""

import math
import os
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

from skyfield.api import wgs84
from skyfield.sgp4lib import EarthSatellite

from py_stars.ephemeris import DEFAULT_EPHEMERIS_DIR, get_ephemeris_context

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_TLE_DIR = os.path.join(PROJECT_ROOT, "data", "tles")

DEFAULT_SAMPLE_TLE = """ISS (ZARYA)
1 25544U 98067A   26226.50000000  .00016717  00000+0  30000-3 0  9993
2 25544  51.6416 180.1234 0004567  85.1234 275.1234 15.49876543456789
TIANGONG (CSS)
1 48274U 21035A   26226.50000000  .00021543  00000+0  25000-3 0  9991
2 48274  41.4721 165.3421 0005123 110.2312 250.1234 15.60123456182345
HST (HUBBLE)
1 20580U 90037B   26226.50000000  .00000843  00000+0  32100-4 0  9998
2 20580  28.4690 120.5123 0002890 290.1234  70.5432 15.08765432890123
STARLINK-1007
1 44713U 19074A   26226.50000000  .00001521  00000+0  85400-4 0  9992
2 44713  53.0543 145.2134 0001423 120.5432 239.5678 15.06432109234567
"""

CELESTRAK_GROUPS: dict[str, str] = {
    "visual": "https://celestrak.org/NORAD/elements/gp.php?GROUP=visual&FORMAT=tle",
    "stations": "https://celestrak.org/NORAD/elements/gp.php?GROUP=stations&FORMAT=tle",
    "starlink": "https://celestrak.org/NORAD/elements/gp.php?GROUP=starlink&FORMAT=tle",
    "active": "https://celestrak.org/NORAD/elements/gp.php?GROUP=active&FORMAT=tle",
    "weather": "https://celestrak.org/NORAD/elements/gp.php?GROUP=weather&FORMAT=tle",
    "brightest": "https://celestrak.org/NORAD/elements/gp.php?GROUP=visual&FORMAT=tle",
}


@dataclass
class SatelliteWaypoint:
    """A point along a satellite's track at a specific time."""

    utc_datetime: datetime
    ra_deg: float
    dec_deg: float
    alt_deg: float
    az_deg: float
    range_km: float
    px: float | None  # Center-origin X [-W/2, +W/2]
    py: float | None  # Center-origin Y [-H/2, +H/2]
    image_x: float | None  # Top-left X [0, W]
    image_y: float | None  # Top-left Y [0, H]
    is_in_fov: bool


@dataclass
class SatellitePass:
    """Satellite orbit pass and streak trajectory within an exposure window."""

    name: str
    norad_cat_id: int
    satellite: EarthSatellite
    epoch_utc: datetime
    # Mid-exposure properties
    mid_utc: datetime
    mid_ra_deg: float
    mid_dec_deg: float
    mid_alt_deg: float
    mid_az_deg: float
    mid_range_km: float
    is_sunlit: bool
    # Streak trajectory
    exposure_seconds: float
    waypoints: list[SatelliteWaypoint] = field(default_factory=list)
    # Image streak coordinates (start to end)
    start_image_xy: tuple[float, float] | None = None
    end_image_xy: tuple[float, float] | None = None
    streak_length_px: float = 0.0
    streak_length_arcmin: float = 0.0
    is_in_fov: bool = False


@dataclass
class SatelliteMatch:
    """Correlation between a satellite streak/position and detected image centroid."""

    satellite_pass: SatellitePass
    centroid_idx: int
    centroid_x: float
    centroid_y: float
    centroid_brightness: float
    min_distance_px: float
    min_distance_arcsec: float
    is_streak_match: bool


@dataclass
class SatelliteMatchResult:
    """Summary of satellite search and correlation in an image."""

    total_propagated: int
    above_horizon_count: int
    in_fov_count: int
    passes: list[SatellitePass] = field(default_factory=list)
    matches: list[SatelliteMatch] = field(default_factory=list)


def download_tle_group(
    group: str = "visual",
    tle_dir: str = DEFAULT_TLE_DIR,
    force_download: bool = False,
    timeout_sec: float = 8.0,
) -> str:
    """Fetch TLE file from CelesTrak or use local cached copy.

    Args:
        group: Group name ('visual', 'stations', 'starlink', 'active', 'weather') or direct URL.
        tle_dir: Local directory for caching TLE files.
        force_download: If True, re-downloads even if cached file exists.
        timeout_sec: HTTP request timeout in seconds.

    Returns:
        Path to the saved/cached TLE text file.
    """
    os.makedirs(tle_dir, exist_ok=True)

    # Determine URL and local filename
    if group in CELESTRAK_GROUPS:
        url = CELESTRAK_GROUPS[group]
        filename = f"celestrak_{group}.tle"
    elif group.startswith("http://") or group.startswith("https://"):
        url = group
        filename = "custom_downloaded.tle"
    else:
        # Assume it's a local file path
        if os.path.exists(group):
            return group
        url = CELESTRAK_GROUPS.get("visual", "")
        filename = f"celestrak_{group}.tle"

    local_path = os.path.join(tle_dir, filename)

    # Check if local cache is fresh (less than 24 hours old)
    if not force_download and os.path.exists(local_path):
        mtime = os.path.getmtime(local_path)
        age_hours = (datetime.now().timestamp() - mtime) / 3600.0
        if age_hours < 24.0:
            return local_path

    # Try downloading
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "py-stars/0.3.0"})
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            content = resp.read().decode("utf-8")
        with open(local_path, "w", encoding="utf-8") as f:
            f.write(content)
        return local_path
    except Exception:
        # Fallback to existing cache, or generate bundled sample TLE file
        if os.path.exists(local_path):
            return local_path
        sample_path = os.path.join(tle_dir, "sample_satellites.tle")
        if not os.path.exists(sample_path):
            try:
                with open(sample_path, "w", encoding="utf-8") as f:
                    f.write(DEFAULT_SAMPLE_TLE)
            except Exception:
                pass
        if os.path.exists(sample_path):
            return sample_path
        return DEFAULT_SAMPLE_TLE


def parse_tle_data(
    filepath_or_text: str,
    ts: Any = None,
    ephemeris_dir: str = DEFAULT_EPHEMERIS_DIR,
) -> list[EarthSatellite]:
    """Parse TLE text or file into Skyfield EarthSatellite objects.

    Supports both 3-line format (0: Name, 1: Line1, 2: Line2) and 2-line format.

    Args:
        filepath_or_text: Path to TLE file or multiline TLE string.
        ts: Skyfield timescale object.
        ephemeris_dir: Path for ephemeris context if ts is None.

    Returns:
        List of EarthSatellite objects.
    """
    if ts is None:
        _, ts, _ = get_ephemeris_context(ephemeris_dir)

    if os.path.exists(filepath_or_text):
        with open(filepath_or_text, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
    else:
        text = filepath_or_text

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    satellites: list[EarthSatellite] = []

    i = 0
    while i < len(lines):
        # Check if 3-line format: line 0 is name, line 1 starts with '1 ', line 2 starts with '2 '
        if i + 2 < len(lines) and lines[i + 1].startswith("1 ") and lines[i + 2].startswith("2 "):
            name = lines[i]
            line1 = lines[i + 1]
            line2 = lines[i + 2]
            try:
                sat = EarthSatellite(line1, line2, name, ts)
                satellites.append(sat)
            except Exception:
                pass
            i += 3
        # 2-line format
        elif i + 1 < len(lines) and lines[i].startswith("1 ") and lines[i + 1].startswith("2 "):
            line1 = lines[i]
            line2 = lines[i + 1]
            try:
                # Infer catalog number as name
                cat_id = line1[2:7].strip()
                sat = EarthSatellite(line1, line2, f"NORAD {cat_id}", ts)
                satellites.append(sat)
            except Exception:
                pass
            i += 2
        else:
            i += 1

    return satellites


def propagate_satellite_trajectory(
    satellite: EarthSatellite,
    lat_deg: float,
    lon_deg: float,
    alt_m: float,
    utc_dt: datetime,
    exposure_seconds: float = 0.0,
    solve_result: Any = None,
    image_width: int = 4032,
    image_height: int = 3024,
    num_steps: int = 11,
    ephemeris: Any = None,
    ts: Any = None,
) -> SatellitePass | None:
    """Propagate a satellite across an exposure window and calculate coordinates.

    Args:
        satellite: Skyfield EarthSatellite object.
        lat_deg: Observer latitude in degrees.
        lon_deg: Observer longitude in degrees.
        alt_m: Observer altitude above sea level in meters.
        utc_dt: Start time of the exposure (or snapshot time).
        exposure_seconds: Exposure duration in seconds (0 for instantaneous snapshot).
        solve_result: Optional tetra3rs.SolveResult for image projection.
        image_width: Image width in pixels.
        image_height: Image height in pixels.
        num_steps: Number of waypoints along the streak.
        ephemeris: Optional JPL ephemeris for sunlit check.
        ts: Skyfield timescale object.

    Returns:
        SatellitePass instance or None if propagation fails.
    """
    if utc_dt.tzinfo is None:
        utc_dt = utc_dt.replace(tzinfo=timezone.utc)

    if ts is None:
        _, ts, _ = get_ephemeris_context()

    observer = wgs84.latlon(lat_deg, lon_deg, elevation_m=alt_m)

    # Determine time steps
    exp_dur = max(0.0, float(exposure_seconds))
    if exp_dur > 0:
        step_dt = exp_dur / max(1, num_steps - 1)
        time_offsets = [i * step_dt for i in range(num_steps)]
    else:
        time_offsets = [0.0]

    w = float(image_width)
    h = float(image_height)
    half_w = w / 2.0
    half_h = h / 2.0

    waypoints: list[SatelliteWaypoint] = []
    any_in_fov = False

    for dt_sec in time_offsets:
        cur_dt = utc_dt + timedelta(seconds=dt_sec)
        t = ts.from_datetime(cur_dt)

        diff = satellite - observer
        topocentric = diff.at(t)

        alt, az, dist = topocentric.altaz()
        ra, dec, _ = topocentric.radec()

        ra_deg = ra._degrees % 360.0
        dec_deg = dec.degrees
        alt_deg = alt.degrees
        az_deg = az.degrees % 360.0
        range_km = dist.km

        px, py = None, None
        img_x, img_y = None, None
        is_in_fov = False

        if solve_result is not None:
            try:
                px_val, py_val = solve_result.world_to_pixel(ra_deg, dec_deg)
                px = float(px_val)
                py = float(py_val)
                if -half_w <= px <= half_w and -half_h <= py <= half_h:
                    is_in_fov = True
                    any_in_fov = True
                    img_x = px + half_w
                    img_y = py + half_h
            except Exception:
                pass

        waypoints.append(
            SatelliteWaypoint(
                utc_datetime=cur_dt,
                ra_deg=ra_deg,
                dec_deg=dec_deg,
                alt_deg=alt_deg,
                az_deg=az_deg,
                range_km=range_km,
                px=px,
                py=py,
                image_x=img_x,
                image_y=img_y,
                is_in_fov=is_in_fov,
            )
        )

    if not waypoints:
        return None

    # Midpoint values
    mid_idx = len(waypoints) // 2
    mid_wp = waypoints[mid_idx]

    # Sunlit calculation
    is_sunlit = True
    if ephemeris is not None:
        try:
            mid_t = ts.from_datetime(mid_wp.utc_datetime)
            is_sunlit = bool(satellite.at(mid_t).is_sunlit(ephemeris))
        except Exception:
            pass

    # Streak endpoints & length
    start_xy = None
    end_xy = None
    streak_len_px = 0.0
    streak_len_arcmin = 0.0

    if len(waypoints) > 1 and solve_result is not None:
        first_wp = waypoints[0]
        last_wp = waypoints[-1]
        if first_wp.image_x is not None and last_wp.image_x is not None:
            start_xy = (first_wp.image_x, first_wp.image_y)
            end_xy = (last_wp.image_x, last_wp.image_y)
            dx = last_wp.image_x - first_wp.image_x
            dy = last_wp.image_y - first_wp.image_y
            streak_len_px = math.hypot(dx, dy)
            scale_arcmin_per_px = (solve_result.fov_deg * 60.0) / w
            streak_len_arcmin = streak_len_px * scale_arcmin_per_px

    # Epoch UTC
    epoch_dt = satellite.epoch.utc_datetime() if hasattr(satellite, "epoch") else utc_dt
    cat_id = getattr(satellite.model, "satnum", 0)

    return SatellitePass(
        name=satellite.name,
        norad_cat_id=cat_id,
        satellite=satellite,
        epoch_utc=epoch_dt,
        mid_utc=mid_wp.utc_datetime,
        mid_ra_deg=mid_wp.ra_deg,
        mid_dec_deg=mid_wp.dec_deg,
        mid_alt_deg=mid_wp.alt_deg,
        mid_az_deg=mid_wp.az_deg,
        mid_range_km=mid_wp.range_km,
        is_sunlit=is_sunlit,
        exposure_seconds=exp_dur,
        waypoints=waypoints,
        start_image_xy=start_xy,
        end_image_xy=end_xy,
        streak_length_px=streak_len_px,
        streak_length_arcmin=streak_len_arcmin,
        is_in_fov=any_in_fov,
    )


def query_satellites_in_fov(
    satellites: list[EarthSatellite],
    lat_deg: float,
    lon_deg: float,
    alt_m: float,
    utc_dt: datetime,
    solve_result: Any,
    image_width: int = 4032,
    image_height: int = 3024,
    exposure_seconds: float = 0.0,
    min_altitude_deg: float = 0.0,
    only_sunlit: bool = False,
    ephemeris: Any = None,
    ts: Any = None,
) -> SatelliteMatchResult:
    """Find all satellites visible in the camera FOV for an exposure.

    Args:
        satellites: List of EarthSatellite objects.
        lat_deg: Observer latitude in degrees.
        lon_deg: Observer longitude in degrees.
        alt_m: Observer altitude in meters.
        utc_dt: UTC datetime of observation.
        solve_result: Solved plate result.
        image_width: Image width in pixels.
        image_height: Image height in pixels.
        exposure_seconds: Exposure time in seconds.
        min_altitude_deg: Minimum altitude above horizon (default 0°).
        only_sunlit: Filter for satellites illuminated by the Sun.
        ephemeris: Optional JPL ephemeris for sunlit check.
        ts: Skyfield timescale object.

    Returns:
        SatelliteMatchResult containing all matching satellite passes.
    """
    if ts is None or ephemeris is None:
        _, ts, eph = get_ephemeris_context()
        if ephemeris is None:
            ephemeris = eph

    total_count = len(satellites)
    above_horizon = 0
    in_fov_passes: list[SatellitePass] = []

    for sat in satellites:
        pass_res = propagate_satellite_trajectory(
            satellite=sat,
            lat_deg=lat_deg,
            lon_deg=lon_deg,
            alt_m=alt_m,
            utc_dt=utc_dt,
            exposure_seconds=exposure_seconds,
            solve_result=solve_result,
            image_width=image_width,
            image_height=image_height,
            ephemeris=ephemeris,
            ts=ts,
        )

        if pass_res is None:
            continue

        if pass_res.mid_alt_deg >= min_altitude_deg:
            above_horizon += 1

            if only_sunlit and not pass_res.is_sunlit:
                continue

            if pass_res.is_in_fov:
                in_fov_passes.append(pass_res)

    return SatelliteMatchResult(
        total_propagated=total_count,
        above_horizon_count=above_horizon,
        in_fov_count=len(in_fov_passes),
        passes=in_fov_passes,
    )


def match_satellites_with_centroids(
    satellite_passes: list[SatellitePass],
    centroids: list[Any],
    image_width: int,
    image_height: int,
    solve_result: Any,
    max_match_radius_px: float = 15.0,
) -> list[SatelliteMatch]:
    """Correlate propagated satellite streaks/points with detected image centroids.

    Args:
        satellite_passes: List of SatellitePass objects inside the image frame.
        centroids: List of detected tetra3rs.Centroid objects.
        image_width: Image width in pixels.
        image_height: Image height in pixels.
        solve_result: Plate solve result.
        max_match_radius_px: Maximum pixel distance to associate a centroid with a satellite.

    Returns:
        List of SatelliteMatch objects.
    """
    if not satellite_passes or not centroids:
        return []

    w = float(image_width)
    h = float(image_height)
    half_w = w / 2.0
    half_h = h / 2.0
    pixel_scale_arcsec = (solve_result.fov_deg * 3600.0) / w

    matches: list[SatelliteMatch] = []

    for sat_pass in satellite_passes:
        # Collect valid image points along the waypoint streak
        pts = [
            (wp.image_x, wp.image_y)
            for wp in sat_pass.waypoints
            if wp.image_x is not None and wp.image_y is not None
        ]

        if not pts:
            continue

        for c_idx, cent in enumerate(centroids):
            # Centroid top-left pixel coordinates
            cx = cent.x + half_w
            cy = cent.y + half_h

            min_dist = float("inf")

            # Check distance to waypoint points or line segments
            if len(pts) == 1:
                min_dist = math.hypot(cx - pts[0][0], cy - pts[0][1])
            else:
                for i in range(len(pts) - 1):
                    p1 = pts[i]
                    p2 = pts[i + 1]
                    # Point to line segment distance
                    dx = p2[0] - p1[0]
                    dy = p2[1] - p1[1]
                    seg_len_sq = dx * dx + dy * dy
                    if seg_len_sq < 1e-6:
                        d = math.hypot(cx - p1[0], cy - p1[1])
                    else:
                        t = max(0.0, min(1.0, ((cx - p1[0]) * dx + (cy - p1[1]) * dy) / seg_len_sq))
                        proj_x = p1[0] + t * dx
                        proj_y = p1[1] + t * dy
                        d = math.hypot(cx - proj_x, cy - proj_y)
                    if d < min_dist:
                        min_dist = d

            if min_dist <= max_match_radius_px:
                matches.append(
                    SatelliteMatch(
                        satellite_pass=sat_pass,
                        centroid_idx=c_idx,
                        centroid_x=cx,
                        centroid_y=cy,
                        centroid_brightness=cent.brightness,
                        min_distance_px=min_dist,
                        min_distance_arcsec=min_dist * pixel_scale_arcsec,
                        is_streak_match=(len(pts) > 1),
                    )
                )

    return matches
