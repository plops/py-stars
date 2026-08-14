#!/usr/bin/env python3
"""Multi-frame camera calibration and lens distortion analysis for iPhone star photos."""

import glob
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from py_stars.heic_loader import get_image_info, load_heic_as_uint8
from py_stars.plate_solver import (
    IPHONE11_HFOV,
    get_or_create_database,
    solve_image,
)
from py_stars.star_detector import extract_centroids_tetra3
from py_stars.visualizer import ensure_output_dir


def main():
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_dir = os.path.join(project_root, "output")
    ensure_output_dir(output_dir)

    db_path = os.path.join(project_root, "data", "iphone_wide.bin")
    db = get_or_create_database(db_path)

    # Candidate images
    candidate_paths = (
        glob.glob(os.path.join(project_root, "data", "*.HEIC"))
        + glob.glob(os.path.join(project_root, "data", "*.heic"))
        + ["/workspace/src/IMG_8556.HEIC"]
    )
    files = sorted(list(set([f for f in candidate_paths if os.path.exists(f)])))

    print(f"Processing all {len(files)} HEIC files...")
    w, h = 4032, 3024

    results_uncal = []
    centroids_list = []
    image_names = []
    exif_infos = []

    for f in files:
        fname = os.path.basename(f)
        gray = load_heic_as_uint8(f)
        ext = extract_centroids_tetra3(gray, sigma_threshold=10.0, max_centroids=80)
        res = solve_image(
            db, ext.centroids, image_width=w, image_height=h, fov_estimate_deg=IPHONE11_HFOV
        )
        if res:
            results_uncal.append(res)
            centroids_list.append(ext.centroids)
            image_names.append(fname)
            exif_infos.append(get_image_info(f))
            print(
                f"  [Solved] {fname:14s}: {res.num_matches:2d} matches, "
                f'RA={res.ra_deg:6.2f}°, Dec={res.dec_deg:+6.2f}°, RMSE={res.rmse_arcsec:6.1f}"'
            )
        else:
            print(f"  [Failed] {fname:14s}")

    print(f"\nFitting global camera models across {len(results_uncal)} images...")
    cal_rad = db.calibrate_camera(
        results_uncal, centroids_list, image_width=w, image_height=h, model="radial"
    )
    cal_poly = db.calibrate_camera(
        results_uncal, centroids_list, image_width=w, image_height=h, model="polynomial", order=3
    )

    print("Radial Model:", cal_rad)
    print("Poly Model:  ", cal_poly)

    # Save camera models
    cal_rad.camera_model.save_to_file(
        os.path.join(project_root, "data", "iphone11_camera_radial.bin")
    )
    cal_poly.camera_model.save_to_file(
        os.path.join(project_root, "data", "iphone11_camera_poly.bin")
    )

    # Evaluate all images with calibrated models
    uncal_rmses = []
    rad_rmses = []
    poly_rmses = []

    print("\n--- Comparative Per-Image Results ---")
    for i, fname in enumerate(image_names):
        res_u = results_uncal[i]
        res_r = db.solve_from_centroids(centroids_list[i], camera_model=cal_rad.camera_model)
        res_p = db.solve_from_centroids(centroids_list[i], camera_model=cal_poly.camera_model)

        u_val = res_u.rmse_arcsec if res_u else np.nan
        r_val = res_r.rmse_arcsec if res_r else np.nan
        p_val = res_p.rmse_arcsec if res_p else np.nan

        uncal_rmses.append(u_val)
        rad_rmses.append(r_val)
        poly_rmses.append(p_val)
        print(f'{fname:14s} | Uncal: {u_val:6.1f}" | Radial: {r_val:6.1f}" | Poly: {p_val:6.1f}"')

    # ============================================================================
    # Generate Comprehensive Distortion & Analysis Plot
    # ============================================================================
    fig = plt.figure(figsize=(18, 12), dpi=150)
    fig.patch.set_facecolor("#0f141d")

    # 1. 2D Distortion Vector Field (Quiver Plot)
    ax1 = fig.add_subplot(2, 2, 1)
    ax1.set_facecolor("#1a2130")
    grid_x, grid_y = np.meshgrid(np.linspace(-w / 2, w / 2, 25), np.linspace(-h / 2, h / 2, 19))
    dist = cal_rad.camera_model.distortion
    dx_grid = np.zeros_like(grid_x)
    dy_grid = np.zeros_like(grid_y)
    mag_grid = np.zeros_like(grid_x)

    for iy in range(grid_x.shape[0]):
        for ix in range(grid_x.shape[1]):
            px, py = grid_x[iy, ix], grid_y[iy, ix]
            dpx, dpy = dist.distort(px, py)
            dx_grid[iy, ix] = dpx - px
            dy_grid[iy, ix] = dpy - py
            mag_grid[iy, ix] = np.hypot(dpx - px, dpy - py)

    im1 = ax1.imshow(
        mag_grid, extent=[-w / 2, w / 2, -h / 2, h / 2], origin="lower", cmap="plasma", alpha=0.85
    )
    cb1 = plt.colorbar(im1, ax=ax1, fraction=0.046, pad=0.04)
    cb1.set_label("Verzeichnung / Versatz (Pixel)", color="#e0e6ed", fontsize=10)
    cb1.ax.tick_params(colors="#e0e6ed")

    # Quiver arrows
    ax1.quiver(grid_x, grid_y, dx_grid, dy_grid, color="cyan", scale=400, width=0.003, alpha=0.9)
    ax1.set_title(
        "Objektiv-Verzeichnungsfeld (iPhone 11 Weitwinkel)",
        color="#ffffff",
        fontsize=13,
        fontweight="bold",
        pad=10,
    )
    ax1.set_xlabel("Sensor X (Pixel von Bildmitte)", color="#e0e6ed", fontsize=10)
    ax1.set_ylabel("Sensor Y (Pixel von Bildmitte)", color="#e0e6ed", fontsize=10)
    ax1.tick_params(colors="#a0aec0")
    ax1.grid(True, linestyle="--", alpha=0.2, color="#ffffff")

    # 2. Radial Distortion Profile Δr vs Radius
    ax2 = fig.add_subplot(2, 2, 2)
    ax2.set_facecolor("#1a2130")
    r_vals = np.linspace(0, np.hypot(w / 2, h / 2), 200)
    dr_radial = []
    for r in r_vals:
        x, y = r / np.sqrt(2), r / np.sqrt(2)
        dx, dy = dist.distort(x, y)
        dr_radial.append(r - np.hypot(dx, dy))

    ax2.plot(
        r_vals, dr_radial, color="#00d2ff", linewidth=2.5, label="Radial Model (Brown-Conrady)"
    )
    ax2.axvline(w / 2, color="#ff9f43", linestyle="--", label=f"Sensorrand X ({w / 2:.0f} px)")
    ax2.axvline(
        np.hypot(w / 2, h / 2),
        color="#ee5253",
        linestyle=":",
        label=f"Sensorecke ({np.hypot(w / 2, h / 2):.0f} px)",
    )
    ax2.set_title(
        "Radiale Verschiebung dr ueber Sensorradius",
        color="#ffffff",
        fontsize=13,
        fontweight="bold",
        pad=10,
    )
    ax2.set_xlabel("Abstand von der Bildmitte r (Pixel)", color="#e0e6ed", fontsize=10)
    ax2.set_ylabel("Tonnenverzeichnung dr (Pixel)", color="#e0e6ed", fontsize=10)
    ax2.tick_params(colors="#a0aec0")
    ax2.grid(True, linestyle="--", alpha=0.2, color="#ffffff")
    ax2.legend(facecolor="#0f141d", edgecolor="#2d3748", labelcolor="#e0e6ed", loc="upper left")

    # 3. RMSE Comparison per Image (Bar Chart)
    ax3 = fig.add_subplot(2, 2, 3)
    ax3.set_facecolor("#1a2130")
    x_indices = np.arange(len(image_names))
    bar_width = 0.28

    ax3.bar(
        x_indices - bar_width,
        uncal_rmses,
        bar_width,
        label="Unkalibriert (Pinhole)",
        color="#ee5253",
        alpha=0.85,
    )
    ax3.bar(x_indices, rad_rmses, bar_width, label="Radial kalibriert", color="#0abde3", alpha=0.85)
    ax3.bar(
        x_indices + bar_width,
        poly_rmses,
        bar_width,
        label="Polynom kalibriert (Ord 3)",
        color="#10ac84",
        alpha=0.85,
    )

    ax3.set_title(
        "Plate-Solving Genauigkeit (RMSE in Bogensekunden)",
        color="#ffffff",
        fontsize=13,
        fontweight="bold",
        pad=10,
    )
    ax3.set_ylabel("RMSE (Bogensekunden)", color="#e0e6ed", fontsize=10)
    ax3.set_xticks(x_indices)
    ax3.set_xticklabels(
        [f.replace(".HEIC", "") for f in image_names],
        rotation=35,
        ha="right",
        color="#e0e6ed",
        fontsize=9,
    )
    ax3.tick_params(colors="#a0aec0")
    ax3.grid(True, linestyle="--", alpha=0.2, color="#ffffff")
    ax3.legend(facecolor="#0f141d", edgecolor="#2d3748", labelcolor="#e0e6ed")

    # 4. Sky Map / RA-Dec Pointings
    ax4 = fig.add_subplot(2, 2, 4)
    ax4.set_facecolor("#1a2130")
    ras = [r.ra_deg for r in results_uncal]
    decs = [r.dec_deg for r in results_uncal]
    matches = [r.num_matches for r in results_uncal]

    scatter = ax4.scatter(
        ras,
        decs,
        s=[m * 10 for m in matches],
        c=poly_rmses,
        cmap="viridis_r",
        edgecolors="#ffffff",
        linewidth=1.5,
        alpha=0.9,
    )
    cb4 = plt.colorbar(scatter, ax=ax4, fraction=0.046, pad=0.04)
    cb4.set_label("RMSE nach Kalibrierung (Bogensekunden)", color="#e0e6ed", fontsize=10)
    cb4.ax.tick_params(colors="#e0e6ed")

    for i, txt in enumerate(image_names):
        ax4.annotate(
            txt.replace(".HEIC", ""),
            (ras[i] + 2, decs[i] + 1),
            color="#e0e6ed",
            fontsize=8,
            alpha=0.9,
        )

    ax4.set_title(
        "Himmelsabdeckung der 9 iPhone-Aufnahmen",
        color="#ffffff",
        fontsize=13,
        fontweight="bold",
        pad=10,
    )
    ax4.set_xlabel("Rektaszension RA (Grad)", color="#e0e6ed", fontsize=10)
    ax4.set_ylabel("Deklination Dec (Grad)", color="#e0e6ed", fontsize=10)
    ax4.tick_params(colors="#a0aec0")
    ax4.grid(True, linestyle="--", alpha=0.2, color="#ffffff")

    plt.tight_layout(pad=3.0)
    plot_path = os.path.join(output_dir, "distortion_and_multi_frame_analysis.png")
    plt.savefig(plot_path, facecolor=fig.get_facecolor(), edgecolor="none")
    plt.close()
    print(f"\nVisualization successfully saved to: {plot_path}")


if __name__ == "__main__":
    main()
