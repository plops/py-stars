"""Visualization of star detection, plate solving, astrometric accuracy, and detectability."""

import math
import os
from typing import Any

import matplotlib
import matplotlib.pyplot as plt
import numpy as np

# Non-interactive backend
matplotlib.use("Agg")

# Default output directory
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")


def ensure_output_dir(output_dir: str = OUTPUT_DIR) -> str:
    """Create the output directory if it doesn't exist."""
    os.makedirs(output_dir, exist_ok=True)
    return output_dir


def plot_detected_stars(
    image: np.ndarray,
    centroids: list[Any],
    output_path: str,
    title: str = "Detected Stars",
) -> None:
    """Plot the image with detected star positions marked."""
    fig, ax = plt.subplots(1, 1, figsize=(12, 8))
    ax.imshow(image, cmap="gray", origin="upper")

    h, w = image.shape[:2]
    cx, cy = w / 2.0, h / 2.0

    for c in centroids:
        px = c.x + cx
        py = c.y + cy
        circle = plt.Circle((px, py), radius=8, fill=False, color="lime", linewidth=1.5)
        ax.add_patch(circle)

    ax.set_title(f"{title} ({len(centroids)} stars)", fontsize=14)
    ax.set_xlabel("X (pixels)")
    ax.set_ylabel("Y (pixels)")

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_star_brightnesses(
    centroids: list[Any],
    output_path: str,
    title: str = "Star Brightness Distribution",
) -> None:
    """Plot histogram of star brightnesses."""
    if not centroids:
        return

    brightnesses = [c.brightness for c in centroids]

    fig, ax = plt.subplots(1, 1, figsize=(10, 5))
    ax.hist(brightnesses, bins=30, color="steelblue", edgecolor="black", alpha=0.7)
    ax.set_title(title, fontsize=14)
    ax.set_xlabel("Brightness (integrated intensity)")
    ax.set_ylabel("Count")
    ax.axvline(
        np.median(brightnesses),
        color="red",
        linestyle="--",
        label=f"Median: {np.median(brightnesses):.0f}",
    )
    ax.legend()

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def create_summary_image(
    image: np.ndarray,
    centroids: list[Any],
    solve_result: Any,
    output_path: str,
    title: str = "Star Detection & Plate Solve Summary",
) -> None:
    """Create a combined 2-panel summary image with detection overlay and solve info."""
    fig, axes = plt.subplots(1, 2, figsize=(18, 8))

    ax1 = axes[0]
    ax1.imshow(image, cmap="gray", origin="upper")

    h, w = image.shape[:2]
    cx, cy = w / 2.0, h / 2.0

    matched_set = set()
    if solve_result:
        mc = getattr(solve_result, "matched_centroids", None)
        if mc is not None:
            matched_set = {int(i) for i in mc}

    for idx, c in enumerate(centroids):
        px = c.x + cx
        py = c.y + cy
        if idx in matched_set:
            color = "lime"
            radius = 12
            linewidth = 2.0
        else:
            color = "cyan"
            radius = 6
            linewidth = 1.0
        circle = plt.Circle((px, py), radius=radius, fill=False, color=color, linewidth=linewidth)
        ax1.add_patch(circle)

    n_matched = len(matched_set) if matched_set else 0
    ax1.set_title(f"Stars: {len(centroids)} detected, {n_matched} matched", fontsize=12)

    ax2 = axes[1]
    ax2.axis("off")

    if solve_result and hasattr(solve_result, "ra_deg"):
        info_text = (
            "Plate Solve: SUCCESS\n\n"
            f"RA:   {solve_result.ra_deg:.4f}°\n"
            f"Dec:  {solve_result.dec_deg:+.4f}°\n"
            f"Roll: {solve_result.roll_deg:.2f}°\n"
            f"FOV:  {solve_result.fov_deg:.2f}°\n\n"
            f"Matches: {solve_result.num_matches}\n"
            f'RMSE:    {solve_result.rmse_arcsec:.2f}"\n'
            f"Time:    {solve_result.solve_time_ms:.1f}ms\n"
        )
    else:
        status = getattr(solve_result, "status", "unknown")
        info_text = f"Plate Solve: FAILED\nStatus: {status}\n"

    ax2.text(
        0.1,
        0.9,
        info_text,
        transform=ax2.transAxes,
        fontsize=14,
        verticalalignment="top",
        fontfamily="monospace",
        bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.5),
    )

    fig.suptitle(title, fontsize=16, fontweight="bold")
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_cross_match_diagnostics(
    image: np.ndarray,
    solve_result: Any,
    cross_match_result: Any,
    output_path: str,
    title: str = "Astrometric & Completeness Diagnostics",
) -> None:
    """Generate a comprehensive 4-panel diagnostic figure.

    Panels:
    1. Image overlay with matched catalog stars, uncataloged detections, and missed stars.
    2. Astrometric residuals vs radius from image center (evaluating distortion & refraction).
    3. Detection completeness curve vs catalog magnitude (limiting magnitude 50% & 90%).
    4. Instrumental flux vs catalog magnitude photometric calibration.

    Args:
        image: Grayscale numpy array.
        solve_result: SolveResult object.
        cross_match_result: CrossMatchResult object from star_matching.cross_match_stars.
        output_path: Where to save the diagnostic figure.
        title: Overall figure title.
    """
    fig = plt.figure(figsize=(20, 14), dpi=150)
    fig.patch.set_facecolor("#0f141d")

    h, w = image.shape[:2]
    cx, cy = w / 2.0, h / 2.0

    cm = cross_match_result
    matched = cm.matched_stars
    unmatched_cat = cm.unmatched_catalog_stars
    unmatched_det = cm.unmatched_centroids
    lim = cm.limiting_magnitude

    # ------------------------------------------------------------------------
    # Panel 1: Image Overlay & Identification Map
    # ------------------------------------------------------------------------
    ax1 = fig.add_subplot(2, 2, 1)
    ax1.set_facecolor("#000000")
    ax1.imshow(image, cmap="gray", origin="upper", extent=[0, w, h, 0], vmin=0, vmax=255)

    # Plot matched stars (Green)
    if matched:
        px_matched = [p.det_x + cx for p in matched]
        py_matched = [p.det_y + cy for p in matched]
        mags_matched = [p.magnitude for p in matched]
        sizes_m = [max(15.0, 120.0 - m * 15.0) for m in mags_matched]

        ax1.scatter(
            px_matched,
            py_matched,
            s=sizes_m,
            facecolors="none",
            edgecolors="#00ff88",
            linewidth=1.8,
            label=f"Matched Catalog Stars ({len(matched)})",
            zorder=4,
        )

    # Plot uncataloged detections (Cyan crosses)
    if unmatched_det:
        px_unmatched_det = [c["x"] + cx for c in unmatched_det]
        py_unmatched_det = [c["y"] + cy for c in unmatched_det]
        ax1.scatter(
            px_unmatched_det,
            py_unmatched_det,
            s=25,
            color="#00d2ff",
            marker="x",
            linewidth=1.0,
            alpha=0.7,
            label=f"Uncataloged Detections ({len(unmatched_det)})",
            zorder=3,
        )

    # Plot missed bright catalog stars (mag < 5.5, Red dashed)
    missed_bright = [s for s in unmatched_cat if s["magnitude"] < 5.5]
    if missed_bright:
        px_missed = [s["px"] + cx for s in missed_bright]
        py_missed = [s["py"] + cy for s in missed_bright]
        ax1.scatter(
            px_missed,
            py_missed,
            s=60,
            facecolors="none",
            edgecolors="#ff4757",
            linestyle="--",
            linewidth=1.2,
            label=f"Missed Catalog Stars (mag<5.5: {len(missed_bright)})",
            zorder=2,
        )

    # Plot refraction vectors if present
    if cm.applied_refraction and matched:
        ref_stars = [p for p in matched if p.refraction_arcsec > 5.0]
        if ref_stars:
            px_t = [p.proj_x + cx for p in ref_stars]
            py_t = [p.proj_y + cy for p in ref_stars]
            dx_r = [p.dx_px for p in ref_stars]
            dy_r = [p.dy_px for p in ref_stars]
            ax1.quiver(
                px_t,
                py_t,
                dx_r,
                dy_r,
                color="#feca57",
                scale=50,
                width=0.003,
                alpha=0.8,
                label="Refraction Offset Vectors",
            )

    ax1.set_xlim(0, w)
    ax1.set_ylim(h, 0)
    ax1.set_title(
        "Identified Stars & Catalog Overlay", color="#ffffff", fontsize=13, fontweight="bold"
    )
    ax1.set_xlabel("Sensor X (pixels)", color="#e0e6ed", fontsize=10)
    ax1.set_ylabel("Sensor Y (pixels)", color="#e0e6ed", fontsize=10)
    ax1.tick_params(colors="#a0aec0")
    ax1.legend(
        facecolor="#0f141d",
        edgecolor="#2d3748",
        labelcolor="#e0e6ed",
        fontsize=8,
        loc="upper right",
    )

    # ------------------------------------------------------------------------
    # Panel 2: Astrometric Residuals vs Radius from Center
    # ------------------------------------------------------------------------
    ax2 = fig.add_subplot(2, 2, 2)
    ax2.set_facecolor("#1a2130")

    if matched:
        radii_px = np.array([math.hypot(p.proj_x, p.proj_y) for p in matched])
        residuals_arcsec = np.array([p.dist_arcsec for p in matched])
        mags = np.array([p.magnitude for p in matched])

        scatter = ax2.scatter(
            radii_px,
            residuals_arcsec,
            c=mags,
            cmap="viridis_r",
            s=40,
            edgecolor="#ffffff",
            linewidth=0.5,
            alpha=0.9,
        )
        cb = plt.colorbar(scatter, ax=ax2, fraction=0.046, pad=0.04)
        cb.set_label("Catalog Magnitude (mag)", color="#e0e6ed", fontsize=9)
        cb.ax.tick_params(colors="#e0e6ed")

        ax2.axhline(
            cm.rmse_arcsec,
            color="#ff4757",
            linestyle="--",
            linewidth=1.8,
            label=f'Total RMSE: {cm.rmse_arcsec:.1f}" ({cm.rmse_px:.2f} px)',
        )
        ax2.axhline(
            np.median(residuals_arcsec),
            color="#00d2ff",
            linestyle=":",
            linewidth=1.5,
            label=f'Median: {np.median(residuals_arcsec):.1f}" ({cm.median_residual_px:.2f} px)',
        )

    ax2.set_title(
        "Astrometric Residuals vs Sensor Radius", color="#ffffff", fontsize=13, fontweight="bold"
    )
    ax2.set_xlabel("Distance from Optical Center (pixels)", color="#e0e6ed", fontsize=10)
    ax2.set_ylabel('Positional Residual (arcseconds ")', color="#e0e6ed", fontsize=10)
    ax2.tick_params(colors="#a0aec0")
    ax2.grid(True, linestyle="--", alpha=0.2, color="#ffffff")
    ax2.legend(facecolor="#0f141d", edgecolor="#2d3748", labelcolor="#e0e6ed", fontsize=9)

    # ------------------------------------------------------------------------
    # Panel 3: Detection Completeness vs Catalog Magnitude
    # ------------------------------------------------------------------------
    ax3 = fig.add_subplot(2, 2, 3)
    ax3.set_facecolor("#1a2130")

    if lim.mag_bins:
        mag_centers = [b.mag_center for b in lim.mag_bins if b.total_in_frame > 0]
        rates = [b.completeness_rate * 100.0 for b in lim.mag_bins if b.total_in_frame > 0]
        counts = [
            f"{b.detected_count}/{b.total_in_frame}" for b in lim.mag_bins if b.total_in_frame > 0
        ]

        bars = ax3.bar(
            mag_centers,
            rates,
            width=0.42,
            color="#10ac84",
            edgecolor="#ffffff",
            alpha=0.85,
            label="Detection Rate (%)",
        )

        for bar, count in zip(bars, counts, strict=False):
            y_val = bar.get_height()
            ax3.text(
                bar.get_x() + bar.get_width() / 2.0,
                y_val + 2.0,
                count,
                ha="center",
                va="bottom",
                color="#e0e6ed",
                fontsize=8,
            )

        ax3.axhline(
            90.0, color="#2ed573", linestyle="--", alpha=0.8, label="90% Completeness Limit"
        )
        ax3.axhline(
            50.0, color="#ffa502", linestyle="--", alpha=0.8, label="50% Limiting Magnitude"
        )

        if lim.mag_90_completeness:
            ax3.axvline(
                lim.mag_90_completeness,
                color="#2ed573",
                linestyle=":",
                linewidth=2.0,
                label=f"m_90 = {lim.mag_90_completeness:.1f} mag",
            )
        if lim.mag_50_completeness:
            ax3.axvline(
                lim.mag_50_completeness,
                color="#ffa502",
                linestyle=":",
                linewidth=2.0,
                label=f"m_50 = {lim.mag_50_completeness:.1f} mag",
            )

    faintest_text = (
        f"Faintest Detected: {lim.faintest_detected_magnitude:.2f} mag"
        if lim.faintest_detected_magnitude
        else ""
    )
    ax3.set_title(
        f"Detection Completeness vs Magnitude ({faintest_text})",
        color="#ffffff",
        fontsize=13,
        fontweight="bold",
    )
    ax3.set_xlabel("Catalog Magnitude (mag)", color="#e0e6ed", fontsize=10)
    ax3.set_ylabel("Completeness / Detection Rate (%)", color="#e0e6ed", fontsize=10)
    ax3.set_ylim(0, 115)
    ax3.tick_params(colors="#a0aec0")
    ax3.grid(True, linestyle="--", alpha=0.2, color="#ffffff")
    ax3.legend(
        facecolor="#0f141d",
        edgecolor="#2d3748",
        labelcolor="#e0e6ed",
        fontsize=8,
        loc="upper right",
    )

    # ------------------------------------------------------------------------
    # Panel 4: Photometry Calibration (Flux vs Catalog Magnitude)
    # ------------------------------------------------------------------------
    ax4 = fig.add_subplot(2, 2, 4)
    ax4.set_facecolor("#1a2130")

    if matched:
        bright_stars = [p for p in matched if p.det_brightness > 0]
        if bright_stars:
            fluxes = np.array([p.det_brightness for p in bright_stars])
            inst_mags = -2.5 * np.log10(fluxes)
            cat_mags = np.array([p.magnitude for p in bright_stars])

            ax4.scatter(
                cat_mags,
                inst_mags,
                color="#00d2ff",
                edgecolor="#ffffff",
                linewidth=0.5,
                s=40,
                alpha=0.85,
                label=f"Matched Stars (N={len(bright_stars)})",
            )

            if cm.photometry:
                zp = cm.photometry.zero_point
                m_fit = np.linspace(min(cat_mags) - 0.5, max(cat_mags) + 0.5, 100)
                inst_fit = m_fit - zp
                ax4.plot(
                    m_fit,
                    inst_fit,
                    color="#ff4757",
                    linewidth=2.0,
                    label=(
                        f"Calibration: m_inst = m_cat - {zp:.2f} "
                        f"(σ={cm.photometry.photometric_scatter_mag:.2f} mag)"
                    ),
                )

    ax4.set_title(
        "Instrumental Photometry vs Catalog Magnitude",
        color="#ffffff",
        fontsize=13,
        fontweight="bold",
    )
    ax4.set_xlabel("Catalog Magnitude (mag)", color="#e0e6ed", fontsize=10)
    ax4.set_ylabel("Instrumental Magnitude -2.5*log10(Flux)", color="#e0e6ed", fontsize=10)
    ax4.invert_yaxis()
    ax4.tick_params(colors="#a0aec0")
    ax4.grid(True, linestyle="--", alpha=0.2, color="#ffffff")
    ax4.legend(facecolor="#0f141d", edgecolor="#2d3748", labelcolor="#e0e6ed", fontsize=9)

    fig.suptitle(title, fontsize=16, fontweight="bold", color="#ffffff", y=0.99)
    plt.tight_layout(rect=[0, 0, 1, 0.97], pad=2.5)
    plt.savefig(output_path, facecolor=fig.get_facecolor(), edgecolor="none")
    plt.close(fig)
    print(f"Saved diagnostic visualization: {output_path}")


def plot_ephemeris_and_dso_overlay(
    image: np.ndarray,
    solve_result: Any,
    planets: list[Any] | None = None,
    dsos: list[Any] | None = None,
    satellites: list[Any] | None = None,
    centroids: list[Any] | None = None,
    output_path: str = "",
    title: str = "Planets, Deep Sky Objects & Satellites Overlay",
) -> None:
    """Generate high-contrast annotated overlay showing Planets, DSOs, and Satellites in the FOV.

    Args:
        image: Grayscale numpy image array.
        solve_result: Solved SolveResult object.
        planets: List of SolarSystemBodyPosition objects in the FOV.
        dsos: List of ProjectedDSO objects in the FOV.
        satellites: List of SatellitePass objects in the FOV.
        centroids: List of detected star centroids.
        output_path: Filepath for the generated PNG.
        title: Header title.
    """
    fig, ax = plt.subplots(1, 1, figsize=(16, 12), dpi=150)
    fig.patch.set_facecolor("#0b0f19")
    ax.set_facecolor("#000000")

    h, w = image.shape[:2]
    cx, cy = w / 2.0, h / 2.0

    # Display base image
    ax.imshow(image, cmap="gray", origin="upper", extent=[0, w, h, 0], vmin=0, vmax=255)

    # 1. Overlay detected stars (subtle green dots)
    if centroids:
        for c in centroids:
            px = c.x + cx
            py = c.y + cy
            circle = plt.Circle(
                (px, py), radius=4, fill=False, color="#2ed573", linewidth=0.8, alpha=0.5
            )
            ax.add_patch(circle)

    # 2. Overlay Deep Sky Objects (Galaxies: purple, Nebulae: cyan, Clusters: yellow)
    if dsos:
        for p_dso in dsos:
            dso = p_dso.dso
            img_x = p_dso.image_x
            img_y = p_dso.image_y
            r_px = max(12.0, p_dso.major_axis_px / 2.0)

            # Color and styling by DSO type
            if "Galaxy" in dso.obj_type:
                edge_color = "#e056fd"  # Magenta/Purple
                style = "-"
            elif "Nebula" in dso.obj_type or "Remnant" in dso.obj_type:
                edge_color = "#00d2d3"  # Cyan/Teal
                style = "--"
            else:  # Cluster / Star Cloud
                edge_color = "#feca57"  # Gold
                style = ":"

            # Bounding ellipse / circle
            circle = plt.Circle(
                (img_x, img_y),
                radius=r_px,
                fill=False,
                edgecolor=edge_color,
                linestyle=style,
                linewidth=1.8,
                alpha=0.9,
            )
            ax.add_patch(circle)

            # Label
            label_name = f"{dso.id} {dso.name}".strip()
            label_text = f"{label_name}\n({dso.obj_type}, {dso.magnitude:.1f} mag)"
            ax.text(
                img_x + r_px + 8,
                img_y,
                label_text,
                color=edge_color,
                fontsize=9,
                fontweight="bold",
                verticalalignment="center",
                bbox=dict(
                    boxstyle="round,pad=0.2",
                    facecolor="#0b0f19",
                    alpha=0.75,
                    edgecolor=edge_color,
                    lw=0.8,
                ),
            )

    # 3. Overlay Planets & Moon (Bright orange/yellow markers with phase & size info)
    if planets:
        for p in planets:
            if p.image_x is None or p.image_y is None:
                continue
            img_x = p.image_x
            img_y = p.image_y

            # Outer ring
            ring = plt.Circle(
                (img_x, img_y),
                radius=18,
                fill=False,
                edgecolor="#ff9f43",
                linewidth=2.2,
                alpha=0.95,
            )
            ax.add_patch(ring)
            # Center target crosshair
            ax.plot([img_x - 24, img_x + 24], [img_y, img_y], color="#ff9f43", lw=1.2)
            ax.plot([img_x, img_x], [img_y - 24, img_y + 24], color="#ff9f43", lw=1.2)

            mag_str = (
                f", {p.estimated_magnitude:+.1f} mag" if p.estimated_magnitude is not None else ""
            )
            phase_str = (
                f", {p.phase_fraction * 100.0:.0f}% lit" if p.phase_fraction is not None else ""
            )
            p_label = f"★ {p.name.upper()}{mag_str}{phase_str}\nRA {p.ra_hms}, Dec {p.dec_dms}"

            ax.text(
                img_x + 28,
                img_y - 10,
                p_label,
                color="#ff9f43",
                fontsize=10,
                fontweight="bold",
                verticalalignment="center",
                bbox=dict(
                    boxstyle="round,pad=0.3",
                    facecolor="#0b0f19",
                    alpha=0.85,
                    edgecolor="#ff9f43",
                    lw=1.2,
                ),
            )

    # 4. Overlay Satellites (Streak trajectory with directional arrow & ID)
    if satellites:
        for sat in satellites:
            pts = [
                (wp.image_x, wp.image_y)
                for wp in sat.waypoints
                if wp.image_x is not None and wp.image_y is not None
            ]
            if not pts:
                continue

            xs = [pt[0] for pt in pts]
            ys = [pt[1] for pt in pts]

            if len(pts) > 1:
                # Plot streak line
                ax.plot(xs, ys, color="#ff4757", linewidth=2.5, linestyle="-", alpha=0.9)
                # Direction arrow
                mid_i = len(pts) // 2
                dx = pts[-1][0] - pts[0][0]
                dy = pts[-1][1] - pts[0][1]
                if math.hypot(dx, dy) > 5.0:
                    ax.annotate(
                        "",
                        xy=(pts[-1][0], pts[-1][1]),
                        xytext=(pts[mid_i][0], pts[mid_i][1]),
                        arrowprops=dict(arrowstyle="->", color="#ff4757", lw=2.5),
                    )
            else:
                # Single snapshot dot
                ax.plot(xs[0], ys[0], marker="^", color="#ff4757", markersize=10)

            # Label at start point
            label_x = xs[0]
            label_y = ys[0]
            sat_text = (
                f"🛰 {sat.name} [NORAD #{sat.norad_cat_id}]\n"
                f"Alt: {sat.mid_alt_deg:.1f}°, Range: {sat.mid_range_km:.0f}km"
            )
            ax.text(
                label_x - 10,
                label_y - 15,
                sat_text,
                color="#ff6b81",
                fontsize=9,
                fontweight="bold",
                horizontalalignment="right",
                bbox=dict(
                    boxstyle="round,pad=0.2",
                    facecolor="#0b0f19",
                    alpha=0.8,
                    edgecolor="#ff4757",
                    lw=1.0,
                ),
            )

    ax.set_xlim(0, w)
    ax.set_ylim(h, 0)
    ax.set_title(title, color="#ffffff", fontsize=15, fontweight="bold", pad=15)
    ax.set_xlabel("Sensor X (pixels)", color="#e0e6ed", fontsize=10)
    ax.set_ylabel("Sensor Y (pixels)", color="#e0e6ed", fontsize=10)
    ax.tick_params(colors="#a0aec0")

    # Legend handles
    legend_elements = [
        plt.Line2D(
            [0],
            [0],
            marker="o",
            color="w",
            label="Detected Star",
            markerfacecolor="#2ed573",
            markersize=6,
        ),
        plt.Line2D(
            [0],
            [0],
            marker="o",
            color="w",
            label="Planet / Moon",
            markerfacecolor="#ff9f43",
            markersize=9,
        ),
        plt.Line2D(
            [0],
            [0],
            marker="o",
            color="w",
            label="Galaxy (DSO)",
            markerfacecolor="#e056fd",
            markersize=8,
        ),
        plt.Line2D(
            [0],
            [0],
            marker="o",
            color="w",
            label="Nebula (DSO)",
            markerfacecolor="#00d2d3",
            markersize=8,
        ),
        plt.Line2D(
            [0],
            [0],
            marker="o",
            color="w",
            label="Star Cluster (DSO)",
            markerfacecolor="#feca57",
            markersize=8,
        ),
        plt.Line2D([0], [0], color="#ff4757", lw=2, label="Satellite Track"),
    ]
    ax.legend(
        handles=legend_elements,
        facecolor="#0f141d",
        edgecolor="#2d3748",
        labelcolor="#e0e6ed",
        fontsize=9,
        loc="upper right",
    )

    plt.tight_layout()
    plt.savefig(output_path, facecolor=fig.get_facecolor(), edgecolor="none")
    plt.close(fig)
    print(f"Saved ephemeris & DSO overlay: {output_path}")
