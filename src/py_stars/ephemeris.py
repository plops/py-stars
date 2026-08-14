"""Ephemeris calculations for Solar System bodies (Planets, Moon, Sun).

Computes exact topocentric apparent Right Ascension, Declination, Altitude, Azimuth,
illuminated phase, angular diameter, and projection onto plate-solved images.
"""

import math
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from skyfield.api import Loader, wgs84
from skyfield.jpllib import SpiceKernel

# Default ephemeris directory in project data/ephemeris
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_EPHEMERIS_DIR = os.path.join(PROJECT_ROOT, "data", "ephemeris")

# Standard planetary visual magnitude approximation models
PLANETARY_TARGETS = [
    ("Sun", "sun", "Sun"),
    ("Moon", "moon", "Moon"),
    ("Mercury", "mercury", "Mercury"),
    ("Venus", "venus", "Venus"),
    ("Mars", "mars barycenter", "Mars"),
    ("Jupiter", "jupiter barycenter", "Jupiter"),
    ("Saturn", "saturn barycenter", "Saturn"),
    ("Uranus", "uranus barycenter", "Uranus"),
    ("Neptune", "neptune barycenter", "Neptune"),
    ("Pluto", "pluto barycenter", "Pluto"),
]

# Physical radii in km for angular size estimation
BODY_RADII_KM: dict[str, float] = {
    "Sun": 696340.0,
    "Moon": 1737.4,
    "Mercury": 2439.7,
    "Venus": 6051.8,
    "Mars": 3389.5,
    "Jupiter": 69911.0,
    "Saturn": 58232.0,
    "Uranus": 25362.0,
    "Neptune": 24622.0,
    "Pluto": 1188.3,
}


@dataclass
class SolarSystemBodyPosition:
    """Calculated ephemeris position and optical properties for a celestial body."""

    name: str
    target_key: str
    utc_datetime: datetime
    # Topocentric equatorial coordinates (apparent)
    ra_deg: float  # [0, 360)
    dec_deg: float  # [-90, +90]
    ra_hms: str  # e.g. "12h 34m 56.7s"
    dec_dms: str  # e.g. "+12° 34' 56\""
    # Topocentric horizontal coordinates
    alt_deg: float  # [-90, +90]
    az_deg: float  # [0, 360)
    # Physical and observational properties
    distance_au: float
    distance_km: float
    angular_diameter_arcsec: float
    phase_fraction: float | None  # [0.0, 1.0] (fraction of disk illuminated)
    phase_angle_deg: float | None  # Sun-Target-Observer angle
    elongation_deg: float | None  # Target-Observer-Sun angle
    estimated_magnitude: float | None
    # Image projection (if solved)
    px: float | None = None  # Center-origin X in pixels
    py: float | None = None  # Center-origin Y in pixels
    image_x: float | None = None  # Top-left origin X in pixels
    image_y: float | None = None  # Top-left origin Y in pixels
    is_in_fov: bool = False
    is_above_horizon: bool = False


@dataclass
class EphemerisObservationResult:
    """Complete collection of ephemeris calculations for a given observation."""

    utc_datetime: datetime
    observer_latitude_deg: float
    observer_longitude_deg: float
    observer_altitude_m: float
    bodies: list[SolarSystemBodyPosition]
    bodies_in_fov: list[SolarSystemBodyPosition]


# Ephemeris manager singleton cache
_LOADER_INSTANCE: Loader | None = None
_EPHEMERIS_INSTANCE: SpiceKernel | None = None


def get_ephemeris_context(
    ephemeris_dir: str = DEFAULT_EPHEMERIS_DIR,
    bsp_name: str = "de421.bsp",
) -> tuple[Loader, Any, SpiceKernel]:
    """Get or initialize the Skyfield Loader, timescale, and planetary ephemeris kernel.

    Args:
        ephemeris_dir: Directory containing or to store ephemeris bsp and timescale files.
        bsp_name: Name of the JPL ephemeris kernel file (default 'de421.bsp').

    Returns:
        Tuple of (loader, timescale, ephemeris_kernel).
    """
    global _LOADER_INSTANCE, _EPHEMERIS_INSTANCE

    os.makedirs(ephemeris_dir, exist_ok=True)

    if _LOADER_INSTANCE is None:
        _LOADER_INSTANCE = Loader(ephemeris_dir)

    ts = _LOADER_INSTANCE.timescale()

    if _EPHEMERIS_INSTANCE is None:
        bsp_path = os.path.join(ephemeris_dir, bsp_name)
        if os.path.exists(bsp_path):
            _EPHEMERIS_INSTANCE = _LOADER_INSTANCE(bsp_name)
        else:
            # Try to load/download
            try:
                _EPHEMERIS_INSTANCE = _LOADER_INSTANCE(bsp_name)
            except Exception as e:
                # If downloading fails (e.g. offline), try built-in or fall back
                raise RuntimeError(
                    f"Could not load ephemeris file '{bsp_name}' from '{ephemeris_dir}': {e}"
                ) from e

    return _LOADER_INSTANCE, ts, _EPHEMERIS_INSTANCE


def estimate_planet_magnitude(
    name: str,
    distance_to_sun_au: float,
    distance_to_earth_au: float,
    phase_angle_deg: float,
) -> float | None:
    """Estimate apparent visual magnitude of major Solar System bodies."""
    r = distance_to_sun_au
    d = distance_to_earth_au
    i_deg = phase_angle_deg

    if r <= 0 or d <= 0:
        return None

    log_term = 5.0 * math.log10(r * d)

    if name == "Sun":
        return -26.74
    elif name == "Moon":
        # Approximate lunar magnitude based on phase angle
        # Full moon ~ -12.7, Quarter ~ -10.0, Crescent ~ -6.0
        return -12.74 + 0.026 * i_deg + 4.0e-9 * (i_deg**4)
    elif name == "Mercury":
        return -0.42 + log_term + 0.0380 * i_deg - 0.000273 * (i_deg**2) + 0.000002 * (i_deg**3)
    elif name == "Venus":
        return -4.40 + log_term + 0.0009 * i_deg + 0.000239 * (i_deg**2) - 0.00000065 * (i_deg**3)
    elif name == "Mars":
        return -1.52 + log_term + 0.016 * i_deg
    elif name == "Jupiter":
        return -9.40 + log_term + 0.005 * i_deg
    elif name == "Saturn":
        # Simplified Saturn model without ring tilt correction
        return -8.88 + log_term + 0.044 * i_deg
    elif name == "Uranus":
        return -7.19 + log_term + 0.0028 * i_deg
    elif name == "Neptune":
        return -6.87 + log_term + 0.001 * i_deg
    elif name == "Pluto":
        return -1.0 + log_term + 0.041 * i_deg
    return None


def deg_to_hms(deg: float) -> str:
    """Convert degrees to Hour Angle string HHh MMm SS.Ss."""
    deg = deg % 360.0
    hours = deg / 15.0
    h = int(hours)
    rem_m = (hours - h) * 60.0
    m = int(rem_m)
    s = (rem_m - m) * 60.0
    return f"{h:02d}h {m:02d}m {s:04.1f}s"


def deg_to_dms(deg: float) -> str:
    """Convert degrees to Signed DMS string ±DD° MM' SS"."""
    sign = "+" if deg >= 0 else "-"
    abs_deg = abs(deg)
    d = int(abs_deg)
    rem_m = (abs_deg - d) * 60.0
    m = int(rem_m)
    s = (rem_m - m) * 60.0
    return f"{sign}{d:02d}° {m:02d}' {s:04.1f}\""


def query_solar_system_ephemerides(
    utc_dt: datetime,
    lat_deg: float,
    lon_deg: float,
    alt_m: float = 0.0,
    solve_result: Any = None,
    image_width: int | None = None,
    image_height: int | None = None,
    ephemeris_dir: str = DEFAULT_EPHEMERIS_DIR,
) -> EphemerisObservationResult:
    """Compute apparent topocentric ephemerides for all major Solar System bodies.

    Optionally projects bodies onto a plate-solved image plane if solve_result is provided.

    Args:
        utc_dt: Observation UTC datetime.
        lat_deg: Observer latitude in degrees [-90, +90].
        lon_deg: Observer longitude in degrees [-180, +180].
        alt_m: Observer altitude above sea level in meters.
        solve_result: Optional tetra3rs.SolveResult object.
        image_width: Optional image width in pixels.
        image_height: Optional image height in pixels.
        ephemeris_dir: Path to directory caching ephemeris files.

    Returns:
        EphemerisObservationResult containing all calculated body positions.
    """
    if utc_dt.tzinfo is None:
        utc_dt = utc_dt.replace(tzinfo=timezone.utc)

    _, ts, eph = get_ephemeris_context(ephemeris_dir)

    # Observer location on Earth
    earth = eph["earth"]
    sun = eph["sun"]
    observer_location = earth + wgs84.latlon(lat_deg, lon_deg, elevation_m=alt_m)

    # Time object
    t = ts.from_datetime(utc_dt)

    sun_astrometric = observer_location.at(t).observe(sun)
    sun_apparent = sun_astrometric.apparent()
    sun_ra, sun_dec, _ = sun_apparent.radec()

    body_positions: list[SolarSystemBodyPosition] = []
    bodies_in_fov: list[SolarSystemBodyPosition] = []

    w = float(image_width or 4032)
    h = float(image_height or 3024)
    half_w = w / 2.0
    half_h = h / 2.0

    for display_name, target_key, target_name in PLANETARY_TARGETS:
        try:
            target = eph[target_key]
        except KeyError:
            continue

        # Topocentric apparent position
        astrometric = observer_location.at(t).observe(target)
        apparent = astrometric.apparent()

        ra, dec, distance = apparent.radec()
        alt, az, _ = apparent.altaz()

        ra_deg = ra._degrees % 360.0
        dec_deg = dec.degrees
        alt_deg = alt.degrees
        az_deg = az.degrees % 360.0

        dist_au = distance.au
        dist_km = distance.km

        # Physical angular diameter: 2 * atan(radius / distance)
        body_radius = BODY_RADII_KM.get(display_name, 1000.0)
        ang_diam_rad = 2.0 * math.atan(body_radius / dist_km) if dist_km > 0 else 0.0
        ang_diam_arcsec = math.degrees(ang_diam_rad) * 3600.0

        # Phase angle (Sun - Target - Observer)
        phase_angle_deg = None
        phase_fraction = None
        elongation_deg = None
        mag = None

        if display_name == "Sun":
            phase_fraction = 1.0
            phase_angle_deg = 0.0
            elongation_deg = 0.0
            mag = -26.74
        else:
            try:
                # Target heliocentric vector
                target_from_sun = sun.at(t).observe(target)
                r_sun_au = target_from_sun.distance().au

                # Observer from target vector
                observer_from_target = target.at(t).observe(observer_location)
                # Sun from target vector
                sun_from_target = target.at(t).observe(sun)

                # Angle between observer and Sun as seen from target
                phase_angle_deg = observer_from_target.separation_from(sun_from_target).degrees
                # Illuminated fraction = (1 + cos(phase_angle)) / 2
                phase_fraction = (1.0 + math.cos(math.radians(phase_angle_deg))) / 2.0

                # Elongation = angle between target and Sun as seen from observer
                elongation_deg = apparent.separation_from(sun_apparent).degrees

                # Estimate magnitude
                mag = estimate_planet_magnitude(display_name, r_sun_au, dist_au, phase_angle_deg)
            except Exception:
                pass

        # Image projection if solve result is available
        px, py = None, None
        img_x, img_y = None, None
        is_in_fov = False
        is_above_horizon = alt_deg > 0.0

        if solve_result is not None:
            try:
                px_val, py_val = solve_result.world_to_pixel(ra_deg, dec_deg)
                px = float(px_val)
                py = float(py_val)
                if -half_w <= px <= half_w and -half_h <= py <= half_h:
                    is_in_fov = True
                    img_x = px + half_w
                    img_y = py + half_h
            except Exception:
                pass

        pos = SolarSystemBodyPosition(
            name=display_name,
            target_key=target_key,
            utc_datetime=utc_dt,
            ra_deg=ra_deg,
            dec_deg=dec_deg,
            ra_hms=deg_to_hms(ra_deg),
            dec_dms=deg_to_dms(dec_deg),
            alt_deg=alt_deg,
            az_deg=az_deg,
            distance_au=dist_au,
            distance_km=dist_km,
            angular_diameter_arcsec=ang_diam_arcsec,
            phase_fraction=phase_fraction,
            phase_angle_deg=phase_angle_deg,
            elongation_deg=elongation_deg,
            estimated_magnitude=mag,
            px=px,
            py=py,
            image_x=img_x,
            image_y=img_y,
            is_in_fov=is_in_fov,
            is_above_horizon=is_above_horizon,
        )

        body_positions.append(pos)
        if is_in_fov:
            bodies_in_fov.append(pos)

    return EphemerisObservationResult(
        utc_datetime=utc_dt,
        observer_latitude_deg=lat_deg,
        observer_longitude_deg=lon_deg,
        observer_altitude_m=alt_m,
        bodies=body_positions,
        bodies_in_fov=bodies_in_fov,
    )
