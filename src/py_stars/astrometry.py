"""Astronomical coordinate transformations and sidereal time calculations."""

import math
from datetime import datetime


def utc_to_gmst_deg(dt: datetime | tuple[int, int, int, int, int, float]) -> float:
    """Compute Greenwich Mean Sidereal Time (GMST) in degrees from UTC datetime.

    Args:
        dt: datetime object (with tzinfo=UTC or naive treated as UTC) or
            tuple of (year, month, day, hour, minute, second).

    Returns:
        GMST angle in degrees [0, 360).
    """
    if isinstance(dt, datetime):
        year, month, day = dt.year, dt.month, dt.day
        hour = dt.hour
        minute = dt.minute
        second = dt.second + dt.microsecond / 1_000_000.0
    else:
        year, month, day, hour, minute, second = dt

    a = (14 - month) // 12
    y = year + 4800 - a
    m = month + 12 * a - 3
    jdn = day + (153 * m + 2) // 5 + 365 * y + y // 4 - y // 100 + y // 400 - 32045
    jd = jdn + (hour - 12) / 24.0 + minute / 1440.0 + second / 86400.0
    d = jd - 2451545.0
    gmst = (280.46061837 + 360.98564736629 * d) % 360.0
    return gmst


def gmst_to_lst_deg(gmst_deg: float, lon_deg: float) -> float:
    """Compute Local Sidereal Time (LST) in degrees from GMST and longitude."""
    return (gmst_deg + lon_deg) % 360.0


def radec_to_altaz(
    ra_deg: float,
    dec_deg: float,
    lat_deg: float,
    lon_deg: float,
    gmst_deg: float,
) -> tuple[float, float]:
    """Convert celestial equatorial coordinates (RA, Dec) to topocentric (Alt, Az).

    Computes true geometric coordinates (without atmospheric refraction).

    Args:
        ra_deg: Right Ascension in degrees [0, 360).
        dec_deg: Declination in degrees [-90, +90].
        lat_deg: Observer latitude in degrees [-90, +90].
        lon_deg: Observer longitude in degrees [-180, +180] (East is positive).
        gmst_deg: Greenwich Mean Sidereal Time in degrees.

    Returns:
        Tuple of (altitude_deg, azimuth_deg), where:
        - altitude is [-90, +90] (0 = horizon, 90 = zenith)
        - azimuth is [0, 360) (0 = North, 90 = East, 180 = South, 270 = West)
    """
    lst = gmst_to_lst_deg(gmst_deg, lon_deg)
    ha = (lst - ra_deg) % 360.0

    ha_rad = math.radians(ha)
    dec_rad = math.radians(dec_deg)
    lat_rad = math.radians(lat_deg)

    sin_alt = math.sin(dec_rad) * math.sin(lat_rad) + math.cos(dec_rad) * math.cos(
        lat_rad
    ) * math.cos(ha_rad)
    sin_alt = max(-1.0, min(1.0, sin_alt))
    alt_rad = math.asin(sin_alt)
    alt_deg = math.degrees(alt_rad)

    cos_alt = math.cos(alt_rad)
    if cos_alt < 1e-9:
        return alt_deg, 0.0

    cos_az = (math.sin(dec_rad) - math.sin(lat_rad) * sin_alt) / (math.cos(lat_rad) * cos_alt)
    sin_az = -math.cos(dec_rad) * math.sin(ha_rad) / cos_alt

    az_rad = math.atan2(sin_az, cos_az)
    az_deg = math.degrees(az_rad) % 360.0

    return alt_deg, az_deg


def altaz_to_radec(
    alt_deg: float,
    az_deg: float,
    lat_deg: float,
    lon_deg: float,
    gmst_deg: float,
) -> tuple[float, float]:
    """Convert topocentric (Alt, Az) back to equatorial (RA, Dec).

    Args:
        alt_deg: Altitude in degrees [-90, +90].
        az_deg: Azimuth in degrees [0, 360) (North=0, East=90).
        lat_deg: Observer latitude in degrees.
        lon_deg: Observer longitude in degrees.
        gmst_deg: Greenwich Mean Sidereal Time in degrees.

    Returns:
        Tuple of (ra_deg, dec_deg).
    """
    lst = gmst_to_lst_deg(gmst_deg, lon_deg)
    alt_rad = math.radians(alt_deg)
    az_rad = math.radians(az_deg)
    lat_rad = math.radians(lat_deg)

    sin_dec = math.sin(alt_rad) * math.sin(lat_rad) + math.cos(alt_rad) * math.cos(
        lat_rad
    ) * math.cos(az_rad)
    sin_dec = max(-1.0, min(1.0, sin_dec))
    dec_rad = math.asin(sin_dec)
    dec_deg = math.degrees(dec_rad)

    cos_dec = math.cos(dec_rad)
    if cos_dec < 1e-9:
        return 0.0, dec_deg

    sin_ha = -math.sin(az_rad) * math.cos(alt_rad) / cos_dec
    cos_ha = (math.sin(alt_rad) - math.sin(lat_rad) * math.sin(dec_rad)) / (
        math.cos(lat_rad) * cos_dec
    )

    ha_rad = math.atan2(sin_ha, cos_ha)
    ha_deg = math.degrees(ha_rad) % 360.0
    ra_deg = (lst - ha_deg) % 360.0

    return ra_deg, dec_deg
