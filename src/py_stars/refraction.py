"""Atmospheric refraction modeling and coordinate correction."""

import math
from typing import Any

from py_stars.astrometry import altaz_to_radec, radec_to_altaz


def barometric_pressure_hpa(altitude_m: float, sea_level_hpa: float = 1013.25) -> float:
    """Compute standard barometric atmospheric pressure at given altitude.

    Args:
        altitude_m: Observer altitude above sea level in meters.
        sea_level_hpa: Sea-level standard pressure in hPa.

    Returns:
        Atmospheric pressure in hPa (mbar).
    """
    scale_height_m = 8400.0
    return sea_level_hpa * math.exp(-max(altitude_m, -500.0) / scale_height_m)


def atmospheric_refraction_arcmin(
    alt_deg: float,
    pressure_hpa: float = 1013.25,
    temp_c: float = 15.0,
) -> float:
    """Calculate atmospheric refraction in arcminutes using Bennett's empirical formula.

    Includes local ambient temperature and pressure scaling.

    Args:
        alt_deg: Geometric (true) altitude in degrees above horizon.
        pressure_hpa: Ambient barometric pressure in hPa.
        temp_c: Ambient temperature in degrees Celsius.

    Returns:
        Refraction angle in arcminutes (always >= 0, lifting stars upward).
    """
    if alt_deg <= -1.0:
        return 0.0

    h = max(alt_deg, 0.0)
    # Bennett's standard formula (1982) for standard atmosphere (1010 hPa, 10°C)
    r_bennett = 1.0 / math.tan(math.radians(h + 7.31 / (h + 4.4))) + 0.0013515

    # Scale for local temperature and pressure
    p_factor = pressure_hpa / 1010.0
    t_factor = 283.15 / (273.15 + temp_c)

    return max(0.0, r_bennett * p_factor * t_factor)


def apply_refraction_to_radec(
    ra_deg: float,
    dec_deg: float,
    lat_deg: float,
    lon_deg: float,
    gmst_deg: float,
    pressure_hpa: float = 1013.25,
    temp_c: float = 15.0,
) -> tuple[float, float, float, float, float]:
    """Compute apparent (refracted) RA/Dec from true geometric RA/Dec.

    Args:
        ra_deg: True geometric Right Ascension in degrees.
        dec_deg: True geometric Declination in degrees.
        lat_deg: Observer latitude in degrees.
        lon_deg: Observer longitude in degrees.
        gmst_deg: Greenwich Mean Sidereal Time in degrees.
        pressure_hpa: Atmospheric pressure in hPa.
        temp_c: Ambient temperature in Celsius.

    Returns:
        Tuple of:
        - app_ra_deg: Apparent (refracted) Right Ascension in degrees.
        - app_dec_deg: Apparent (refracted) Declination in degrees.
        - true_alt_deg: True geometric altitude in degrees.
        - app_alt_deg: Apparent altitude in degrees.
        - refraction_arcsec: Atmospheric refraction displacement in arcseconds.
    """
    true_alt, true_az = radec_to_altaz(ra_deg, dec_deg, lat_deg, lon_deg, gmst_deg)
    r_arcmin = atmospheric_refraction_arcmin(true_alt, pressure_hpa, temp_c)
    app_alt = true_alt + r_arcmin / 60.0
    app_az = true_az  # Azimuth is invariant under standard plane-parallel atmosphere

    app_ra, app_dec = altaz_to_radec(app_alt, app_az, lat_deg, lon_deg, gmst_deg)
    refraction_arcsec = r_arcmin * 60.0

    return app_ra, app_dec, true_alt, app_alt, refraction_arcsec


def apply_refraction_to_catalog_stars(
    catalog_stars: list[Any],
    lat_deg: float,
    lon_deg: float,
    gmst_deg: float,
    pressure_hpa: float = 1013.25,
    temp_c: float = 15.0,
) -> list[dict[str, Any]]:
    """Apply atmospheric refraction to a list of catalog stars.

    Args:
        catalog_stars: List of CatalogStar objects with attributes (id, ra_deg, dec_deg, magnitude).
        lat_deg: Observer latitude in degrees.
        lon_deg: Observer longitude in degrees.
        gmst_deg: GMST in degrees.
        pressure_hpa: Barometric pressure in hPa.
        temp_c: Ambient temperature in Celsius.

    Returns:
        List of dictionaries with true and apparent positions and refraction info.
    """
    results = []
    for star in catalog_stars:
        app_ra, app_dec, true_alt, app_alt, r_arcsec = apply_refraction_to_radec(
            star.ra_deg,
            star.dec_deg,
            lat_deg,
            lon_deg,
            gmst_deg,
            pressure_hpa=pressure_hpa,
            temp_c=temp_c,
        )
        results.append(
            {
                "id": star.id,
                "magnitude": star.magnitude,
                "true_ra_deg": star.ra_deg,
                "true_dec_deg": star.dec_deg,
                "app_ra_deg": app_ra,
                "app_dec_deg": app_dec,
                "true_alt_deg": true_alt,
                "app_alt_deg": app_alt,
                "refraction_arcsec": r_arcsec,
            }
        )
    return results
