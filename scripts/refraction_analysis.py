#!/usr/bin/env python3
"""Atmospheric refraction correction and analysis for GPS-tagged iPhone star photos."""

import math
import os

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import tetra3rs  # noqa: E402

from py_stars.heic_loader import load_heic_as_uint8  # noqa: E402
from py_stars.plate_solver import IPHONE11_HFOV, get_or_create_database, solve_image  # noqa: E402
from py_stars.star_detector import extract_centroids_tetra3  # noqa: E402
from py_stars.visualizer import ensure_output_dir  # noqa: E402


def gmst_from_utc(year, month, day, hour, minute, second):
    """Compute Greenwich Mean Sidereal Time in degrees."""
    a = (14 - month) // 12
    y = year + 4800 - a
    m = month + 12 * a - 3
    jdn = day + (153 * m + 2) // 5 + 365 * y + y // 4 - y // 100 + y // 400 - 32045
    jd = jdn + (hour - 12) / 24.0 + minute / 1440.0 + second / 86400.0
    d = jd - 2451545.0
    return (280.46061837 + 360.98564736629 * d) % 360.0


def radec_to_altaz(ra_deg, dec_deg, lat_deg, lon_deg, gmst_deg):
    """Convert celestial RA/Dec to topocentric Alt/Az (true geometric without atmosphere)."""
    lst = (gmst_deg + lon_deg) % 360.0
    ha = (lst - ra_deg) % 360.0

    ha_rad = math.radians(ha)
    dec_rad = math.radians(dec_deg)
    lat_rad = math.radians(lat_deg)

    sin_alt = math.sin(dec_rad) * math.sin(lat_rad) + math.cos(dec_rad) * math.cos(
        lat_rad
    ) * math.cos(ha_rad)
    alt_rad = math.asin(np.clip(sin_alt, -1.0, 1.0))
    alt_deg = math.degrees(alt_rad)

    cos_az = (math.sin(dec_rad) - math.sin(lat_rad) * sin_alt) / (
        math.cos(lat_rad) * math.cos(alt_rad)
    )
    sin_az = -math.cos(dec_rad) * math.sin(ha_rad) / math.cos(alt_rad)

    az_rad = math.atan2(sin_az, cos_az)
    az_deg = math.degrees(az_rad) % 360.0

    return alt_deg, az_deg


def altaz_to_radec(alt_deg, az_deg, lat_deg, lon_deg, gmst_deg):
    """Convert topocentric Alt/Az back to celestial RA/Dec."""
    lst = (gmst_deg + lon_deg) % 360.0
    alt_rad = math.radians(alt_deg)
    az_rad = math.radians(az_deg)
    lat_rad = math.radians(lat_deg)

    sin_dec = math.sin(alt_rad) * math.sin(lat_rad) + math.cos(alt_rad) * math.cos(
        lat_rad
    ) * math.cos(az_rad)
    dec_rad = math.asin(np.clip(sin_dec, -1.0, 1.0))
    dec_deg = math.degrees(dec_rad)

    sin_ha = -math.sin(az_rad) * math.cos(alt_rad) / math.cos(dec_rad)
    cos_ha = (math.sin(alt_rad) - math.sin(lat_rad) * math.sin(dec_rad)) / (
        math.cos(lat_rad) * math.cos(dec_rad)
    )

    ha_rad = math.atan2(sin_ha, cos_ha)
    ha_deg = math.degrees(ha_rad) % 360.0
    ra_deg = (lst - ha_deg) % 360.0

    return ra_deg, dec_deg


def atmospheric_refraction_arcmin(alt_deg, pressure_hpa=965.0, temp_c=15.0):
    """Bennett's atmospheric refraction formula scaled for local altitude pressure & temp."""
    if alt_deg <= -0.5:
        return 0.0
    h = max(alt_deg, 0.0)
    r_bennett = 1.0 / math.tan(math.radians(h + 7.31 / (h + 4.4))) + 0.0013515
    p_factor = pressure_hpa / 1010.0
    t_factor = 283.15 / (273.15 + temp_c)
    return r_bennett * p_factor * t_factor


def apply_refraction_to_star(
    ra_deg, dec_deg, lat_deg, lon_deg, gmst_deg, pressure_hpa=965.0, temp_c=15.0
):
    """Given true geometric RA/Dec, calculate apparent (refracted) RA/Dec."""
    true_alt, true_az = radec_to_altaz(ra_deg, dec_deg, lat_deg, lon_deg, gmst_deg)
    r_arcmin = atmospheric_refraction_arcmin(true_alt, pressure_hpa, temp_c)
    app_alt = true_alt + r_arcmin / 60.0
    app_az = true_az  # Azimuth is invariant under horizontal plane atmosphere
    app_ra, app_dec = altaz_to_radec(app_alt, app_az, lat_deg, lon_deg, gmst_deg)
    return app_ra, app_dec, true_alt, app_alt, r_arcmin


def main():
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_dir = os.path.join(project_root, "output")
    ensure_output_dir(output_dir)

    db_path = os.path.join(project_root, "data", "iphone_wide.bin")
    db = get_or_create_database(db_path)

    filepath = os.path.join(project_root, "data", "IMG_9144.HEIC")
    gray = load_heic_as_uint8(filepath)
    h, w = gray.shape

    # GPS location & UTC Time for IMG_9144
    lat = 47.0 + 24.0 / 60.0 + 43.69 / 3600.0  # 47.412136° N
    lon = 9.0 + 37.0 / 60.0 + 51.17 / 3600.0  # 9.630881° E
    alt_m = 405.8  # 405.8m
    pressure_hpa = 1013.25 * math.exp(-alt_m / 8400.0)  # ~965.5 hPa barometric
    temp_c = 16.0
    gmst_deg = gmst_from_utc(2026, 8, 14, 21, 17, 50)

    print(
        f"Site: {lat:.4f}° N, {lon:.4f}° E, Alt: {alt_m:.1f} m, "
        f"P: {pressure_hpa:.1f} hPa, T: {temp_c}°C"
    )
    print(f"GMST: {gmst_deg:.4f}° (LST: {(gmst_deg + lon) % 360.0:.4f}°)")

    # 1. Plate solve sky crop
    sky_crop = gray[:1300, :]
    ext = extract_centroids_tetra3(sky_crop, sigma_threshold=10.0, max_centroids=80)
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
    if not res:
        print("Solve failed")
        return

    print(
        f"Plate Solved: RA={res.ra_deg:.4f}°, Dec={res.dec_deg:+.4f}°, "
        f"Roll={res.roll_deg:.2f}°, FOV={res.fov_deg:.2f}°"
    )

    # 2. Get all catalog stars in FOV (cone search radius ~ 40 deg)
    catalog_stars = db.cone_search(res.ra_deg, res.dec_deg, radius_deg=res.fov_deg * 0.65)
    print(f"Found {len(catalog_stars)} catalog stars in search cone.")

    # 3. Project and apply refraction to all stars
    star_data = []
    for s in catalog_stars:
        px_true, py_true = res.world_to_pixel(s.ra_deg, s.dec_deg)

        if -w / 2 <= px_true <= w / 2 and -h / 2 <= py_true <= h / 2:
            app_ra, app_dec, true_alt, app_alt, r_arcmin = apply_refraction_to_star(
                s.ra_deg, s.dec_deg, lat, lon, gmst_deg, pressure_hpa, temp_c
            )
            px_app, py_app = res.world_to_pixel(app_ra, app_dec)

            dx_px = px_app - px_true
            dy_px = py_app - py_true
            shift_px = math.hypot(dx_px, dy_px)
            shift_arcsec = r_arcmin * 60.0

            star_data.append(
                {
                    "id": s.id,
                    "mag": s.magnitude,
                    "ra_true": s.ra_deg,
                    "dec_true": s.dec_deg,
                    "ra_app": app_ra,
                    "dec_app": app_dec,
                    "true_alt": true_alt,
                    "app_alt": app_alt,
                    "r_arcmin": r_arcmin,
                    "px_true": px_true + w / 2,
                    "py_true": py_true + h / 2,
                    "px_app": px_app + w / 2,
                    "py_app": py_app + h / 2,
                    "shift_px": shift_px,
                    "shift_arcsec": shift_arcsec,
                }
            )

    print(f"Stars visible inside frame: {len(star_data)}")
    min_alt = min(s["true_alt"] for s in star_data)
    max_alt = max(s["true_alt"] for s in star_data)
    print(f"Altitude range in frame: {min_alt:.2f}° to {max_alt:.2f}°")
    min_shift = min(s["shift_arcsec"] for s in star_data)
    max_shift = max(s["shift_arcsec"] for s in star_data)
    print(f'Refraction shift range: {min_shift:.1f}" to {max_shift:.1f}"')
    min_px = min(s["shift_px"] for s in star_data)
    max_px = max(s["shift_px"] for s in star_data)
    print(f"Pixel displacement range: {min_px:.2f} px to {max_px:.2f} px")

    # ============================================================================
    # Comprehensive 4-Panel Visualization Plot
    # ============================================================================
    fig = plt.figure(figsize=(18, 12), dpi=150)
    fig.patch.set_facecolor("#0f141d")

    # Panel 1: Image Overlay with Refraction Vector Arrows
    ax1 = fig.add_subplot(2, 2, 1)
    ax1.set_facecolor("#000000")
    ax1.imshow(gray, cmap="gray", origin="upper", extent=[0, w, h, 0], vmin=0, vmax=255)

    sky_stars = [s for s in star_data if s["py_true"] < 1400 and s["true_alt"] > 0]
    px_t = [s["px_true"] for s in sky_stars]
    py_t = [s["py_true"] for s in sky_stars]
    px_a = [s["px_app"] for s in sky_stars]
    py_a = [s["py_app"] for s in sky_stars]
    mags = [s["mag"] for s in sky_stars]
    dx_vec = [s["px_app"] - s["px_true"] for s in sky_stars]
    dy_vec = [s["py_app"] - s["py_true"] for s in sky_stars]
    sizes = [max(10, 80 - m * 10) for m in mags]

    ax1.scatter(
        px_t,
        py_t,
        s=sizes,
        facecolors="none",
        edgecolors="#ee5253",
        linewidth=1.2,
        label="Wahre geometrische Position (ohne Atmosphaere)",
    )
    ax1.scatter(
        px_a,
        py_a,
        s=sizes,
        color="#00d2ff",
        marker="+",
        linewidth=1.5,
        label="Scheinbare Position (mit Refraktion)",
    )

    ax1.quiver(
        px_t,
        py_t,
        dx_vec,
        dy_vec,
        color="#feca57",
        scale=50,
        width=0.003,
        alpha=0.9,
        label="Refraktions-Vektor (10x vergroessert)",
    )

    ax1.axhline(1400, color="#ff9f43", linestyle="--", alpha=0.7, label="Horizontgrenze")
    ax1.set_xlim(0, w)
    ax1.set_ylim(1600, 0)
    ax1.set_title(
        "IMG_9144: Sterne & Atmosphaerische Refraktions-Verschiebung",
        color="#ffffff",
        fontsize=13,
        fontweight="bold",
        pad=10,
    )
    ax1.set_xlabel("Sensor X (Pixel)", color="#e0e6ed", fontsize=10)
    ax1.set_ylabel("Sensor Y (Pixel)", color="#e0e6ed", fontsize=10)
    ax1.tick_params(colors="#a0aec0")
    ax1.legend(
        facecolor="#0f141d",
        edgecolor="#2d3748",
        labelcolor="#e0e6ed",
        fontsize=8,
        loc="upper right",
    )

    # Panel 2: Refraction Curve R(h) vs Altitude
    ax2 = fig.add_subplot(2, 2, 2)
    ax2.set_facecolor("#1a2130")
    alt_range = np.linspace(1.0, 50.0, 300)
    r_arcmin_curve = [atmospheric_refraction_arcmin(a, pressure_hpa, temp_c) for a in alt_range]
    r_arcsec_curve = [r * 60.0 for r in r_arcmin_curve]

    ax2.plot(
        alt_range,
        r_arcsec_curve,
        color="#00d2ff",
        linewidth=2.5,
        label=f"Refraktion R(h) [P={pressure_hpa:.0f}hPa, T={temp_c}°C]",
    )
    ax2.axvline(10.5, color="#ff9f43", linestyle="--", label="Bildmitten-Elevation (10.5°)")
    ax2.axvline(
        min_alt,
        color="#ee5253",
        linestyle=":",
        label=f"Tiefster Stern ({min_alt:.1f}°)",
    )

    star_alts = [s["true_alt"] for s in star_data]
    star_shifts = [s["shift_arcsec"] for s in star_data]
    ax2.scatter(
        star_alts,
        star_shifts,
        color="#feca57",
        s=30,
        alpha=0.8,
        zorder=5,
        label="Sterne im Bildfeld",
    )

    ax2.set_title(
        "Atmosphaerische Lichtbeugung R ueber Hoehenwinkel h",
        color="#ffffff",
        fontsize=13,
        fontweight="bold",
        pad=10,
    )
    ax2.set_xlabel("Hoehe ueber Horizont h (Grad)", color="#e0e6ed", fontsize=10)
    ax2.set_ylabel('Lichtbeugung R (Bogensekunden ")', color="#e0e6ed", fontsize=10)
    ax2.tick_params(colors="#a0aec0")
    ax2.grid(True, linestyle="--", alpha=0.2, color="#ffffff")

    ax2_px = ax2.twinx()
    ax2_px.set_ylabel("Verschiebung auf iPhone-Sensor (Pixel)", color="#00d2ff", fontsize=10)
    ax2_px.set_ylim(ax2.get_ylim()[0] / 59.3, ax2.get_ylim()[1] / 59.3)
    ax2_px.tick_params(colors="#00d2ff")

    ax2.legend(facecolor="#0f141d", edgecolor="#2d3748", labelcolor="#e0e6ed", loc="upper right")

    # Panel 3: Constellation Deformation ("Atmospheric Squash")
    ax3 = fig.add_subplot(2, 2, 3)
    ax3.set_facecolor("#1a2130")

    bright_stars = [s for s in star_data if s["mag"] < 4.0 and s["py_true"] < 1300]
    ax3.scatter(
        [s["px_true"] for s in bright_stars],
        [s["py_true"] for s in bright_stars],
        color="#ee5253",
        s=80,
        label="Wahre geometrische Positionen",
    )
    ax3.scatter(
        [s["px_app"] for s in bright_stars],
        [s["py_app"] for s in bright_stars],
        color="#00d2ff",
        s=80,
        marker="x",
        linewidth=2,
        label="Scheinbare (refraktierte) Positionen",
    )

    for s in bright_stars:
        ax3.annotate(
            f"Mag {s['mag']:.1f}\n(+{s['shift_px']:.1f}px)",
            (s["px_app"] + 20, s["py_app"] - 10),
            color="#e0e6ed",
            fontsize=8,
        )

    ax3.set_title(
        "Sternbild-Stauchung nahe Horizont (Grosser Baer)",
        color="#ffffff",
        fontsize=13,
        fontweight="bold",
        pad=10,
    )
    ax3.set_xlabel("Sensor X (Pixel)", color="#e0e6ed", fontsize=10)
    ax3.set_ylabel("Sensor Y (Pixel)", color="#e0e6ed", fontsize=10)
    ax3.invert_yaxis()
    ax3.tick_params(colors="#a0aec0")
    ax3.grid(True, linestyle="--", alpha=0.2, color="#ffffff")
    ax3.legend(facecolor="#0f141d", edgecolor="#2d3748", labelcolor="#e0e6ed")

    # Panel 4: Refraction Offset Histogram
    ax4 = fig.add_subplot(2, 2, 4)
    ax4.set_facecolor("#1a2130")
    all_shifts_arcsec = [s["shift_arcsec"] for s in star_data]

    ax4.hist(all_shifts_arcsec, bins=25, color="#10ac84", edgecolor="#ffffff", alpha=0.85)
    mean_shift = np.mean(all_shifts_arcsec)
    median_shift = np.median(all_shifts_arcsec)

    ax4.axvline(
        mean_shift,
        color="#ff9f43",
        linestyle="--",
        linewidth=2,
        label=f'Mittelwert: {mean_shift:.1f}" ({mean_shift / 59.3:.2f} px)',
    )
    ax4.axvline(
        median_shift,
        color="#00d2ff",
        linestyle=":",
        linewidth=2,
        label=f'Median: {median_shift:.1f}" ({median_shift / 59.3:.2f} px)',
    )

    ax4.set_title(
        "Verteilung der Refraktionskorrekturen aller sichtbaren Sterne",
        color="#ffffff",
        fontsize=13,
        fontweight="bold",
        pad=10,
    )
    ax4.set_xlabel('Atmosphaerische Verschiebung (Bogensekunden ")', color="#e0e6ed", fontsize=10)
    ax4.set_ylabel("Anzahl Sterne im Bildfeld", color="#e0e6ed", fontsize=10)
    ax4.tick_params(colors="#a0aec0")
    ax4.grid(True, linestyle="--", alpha=0.2, color="#ffffff")
    ax4.legend(facecolor="#0f141d", edgecolor="#2d3748", labelcolor="#e0e6ed")

    plt.tight_layout(pad=3.0)
    plot_path = os.path.join(output_dir, "atmospheric_refraction_analysis.png")
    plt.savefig(plot_path, facecolor=fig.get_facecolor(), edgecolor="none")
    plt.close()
    print(f"\nRefraction analysis diagram successfully saved to: {plot_path}")


if __name__ == "__main__":
    main()
