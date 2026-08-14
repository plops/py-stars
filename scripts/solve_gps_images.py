#!/usr/bin/env python3
"""Plate solve and compute local Alt/Az coordinates for GPS-tagged iPhone images."""

import math
import os

import tetra3rs

from py_stars.heic_loader import load_heic_as_uint8
from py_stars.plate_solver import IPHONE11_HFOV, get_or_create_database, solve_image
from py_stars.star_detector import extract_centroids_tetra3
from py_stars.visualizer import create_summary_image, ensure_output_dir


def ra_dec_to_alt_az(ra_deg, dec_deg, lat_deg, lon_deg, year, month, day, hour, minute, second):
    """Convert celestial RA/Dec to local Alt/Az given observer location and UTC time."""
    a = (14 - month) // 12
    y = year + 4800 - a
    m = month + 12 * a - 3
    jdn = day + (153 * m + 2) // 5 + 365 * y + y // 4 - y // 100 + y // 400 - 32045
    jd = jdn + (hour - 12) / 24.0 + minute / 1440.0 + second / 86400.0
    d = jd - 2451545.0
    gmst = (280.46061837 + 360.98564736629 * d) % 360.0
    lst = (gmst + lon_deg) % 360.0
    ha = (lst - ra_deg) % 360.0

    ha_rad = math.radians(ha)
    dec_rad = math.radians(dec_deg)
    lat_rad = math.radians(lat_deg)

    sin_alt = math.sin(dec_rad) * math.sin(lat_rad) + math.cos(dec_rad) * math.cos(
        lat_rad
    ) * math.cos(ha_rad)
    alt_rad = math.asin(sin_alt)
    alt_deg = math.degrees(alt_rad)

    cos_az = (math.sin(dec_rad) - math.sin(lat_rad) * sin_alt) / (
        math.cos(lat_rad) * math.cos(alt_rad)
    )
    sin_az = -math.cos(dec_rad) * math.sin(ha_rad) / math.cos(alt_rad)

    az_rad = math.atan2(sin_az, cos_az)
    az_deg = math.degrees(az_rad) % 360.0

    return alt_deg, az_deg


def main():
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_dir = os.path.join(project_root, "output")
    ensure_output_dir(output_dir)

    db_path = os.path.join(project_root, "data", "iphone_wide.bin")
    db = get_or_create_database(db_path)

    files = [
        os.path.join(project_root, "data", "IMG_9144.HEIC"),
        os.path.join(project_root, "data", "IMG_9145.HEIC"),
    ]

    for filepath in files:
        fname = os.path.basename(filepath)
        base = os.path.splitext(fname)[0]
        print("=" * 70)
        gray = load_heic_as_uint8(filepath)
        h, w = gray.shape

        # Sky crop above ground landscape lights (y < 1300)
        sky_crop = gray[:1300, :]
        ext = extract_centroids_tetra3(sky_crop, sigma_threshold=10.0, max_centroids=80)

        # Convert crop centroids to full-image coordinate frame
        adjusted_centroids = []
        for c in ext.centroids:
            row = c.y + 1300 / 2.0
            col = c.x + w / 2.0
            adjusted_centroids.append(
                tetra3rs.Centroid(x=col - w / 2.0, y=row - h / 2.0, brightness=c.brightness)
            )

        res = solve_image(
            db, adjusted_centroids, image_width=w, image_height=h, fov_estimate_deg=IPHONE11_HFOV
        )

        if res:
            print("  Plate Solve Status: SUCCESS")
            print(f"    Matched Stars: {res.num_matches}")
            print(f"    RA:            {res.ra_deg:.4f}°")
            print(f"    Dec:           {res.dec_deg:+.4f}°")
            print(f"    Camera Roll:   {res.roll_deg:.2f}°")
            print(f"    FOV:           {res.fov_deg:.2f}°")
            print(f'    RMSE:          {res.rmse_arcsec:.2f}"')

            # GPS: 47° 24' 43.7" N, 9° 37' 51.17" E
            lat = 47.0 + 24.0 / 60.0 + 43.69 / 3600.0
            lon = 9.0 + 37.0 / 60.0 + 51.17 / 3600.0
            alt_m = 405.8

            compass_heading = 350.17 if fname == "IMG_9144.HEIC" else 346.48

            # Calculate Alt/Az (2026-08-14 21:18:12 UTC)
            sky_alt, sky_az = ra_dec_to_alt_az(
                res.ra_deg, res.dec_deg, lat, lon, 2026, 8, 14, 21, 18, 12
            )

            print("  GPS Location (EXIF):")
            print(f"    Coordinates:   {lat:.6f}° N, {lon:.6f}° E (Elevation: {alt_m:.1f} m)")
            print("    UTC Time:      2026-08-14 21:18:12 UTC")
            print("  Local Pointing (Astrometry vs Compass):")
            print(f"    Camera Center Elevation: {sky_alt:.2f}° above horizon")
            print(f"    Camera Center Azimuth:   {sky_az:.2f}° (North=0°, East=90°)")
            print(f"    iPhone Compass Heading:  {compass_heading:.2f}° (True North)")
            print(f"    Compass Difference:      {abs(sky_az - compass_heading):.2f}°")

            # Save summary image
            out_img = os.path.join(output_dir, f"{base}_summary.png")
            create_summary_image(
                gray, adjusted_centroids, res, out_img, title=f"Summary - {base} (GPS Tagged)"
            )
            print(f"  Summary saved to: {out_img}")
        else:
            print("  Plate Solve Status: FAILED")


if __name__ == "__main__":
    main()
