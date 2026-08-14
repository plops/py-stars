"""Visualize star detection and plate solving results.

Creates annotated images showing detected stars, solve results,
and brightness distributions.
"""

import os

import matplotlib
import matplotlib.pyplot as plt
import numpy as np

# Use non-interactive backend (no display needed)
matplotlib.use("Agg")

# Default output directory
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "output")


def ensure_output_dir(output_dir: str = OUTPUT_DIR) -> str:
    """Create the output directory if it doesn't exist."""
    os.makedirs(output_dir, exist_ok=True)
    return output_dir


def plot_detected_stars(
    image: np.ndarray,
    centroids: list,
    output_path: str,
    title: str = "Detected Stars",
) -> None:
    """Plot the image with detected star positions marked.

    Args:
        image: 2D grayscale numpy array.
        centroids: List of tetra3rs.Centroid objects.
        output_path: Where to save the output image.
        title: Plot title.
    """
    fig, ax = plt.subplots(1, 1, figsize=(12, 8))

    # Show the image
    ax.imshow(image, cmap="gray", origin="upper")

    # Mark centroids (convert from image-center coordinates to pixel coordinates)
    h, w = image.shape[:2]
    cx, cy = w / 2.0, h / 2.0

    for c in centroids:
        # tetra3rs centroids have origin at image center
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
    print(f"Saved: {output_path}")


def plot_star_brightnesses(
    centroids: list,
    output_path: str,
    title: str = "Star Brightness Distribution",
) -> None:
    """Plot histogram of star brightnesses.

    Args:
        centroids: List of tetra3rs.Centroid objects.
        output_path: Where to save the output image.
        title: Plot title.
    """
    if not centroids:
        print("No centroids to plot.")
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
    print(f"Saved: {output_path}")


def create_summary_image(
    image: np.ndarray,
    centroids: list,
    solve_result,
    output_path: str,
    title: str = "Star Detection & Plate Solve Summary",
) -> None:
    """Create a combined summary image with detection overlay and solve info.

    Args:
        image: 2D grayscale numpy array.
        centroids: List of tetra3rs.Centroid objects.
        solve_result: SolveResult or SolveFailure.
        output_path: Where to save the output image.
        title: Plot title.
    """
    fig, axes = plt.subplots(1, 2, figsize=(18, 8))

    # Left: Image with detected stars
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

    # Right: Solve result info
    ax2 = axes[1]
    ax2.axis("off")

    if solve_result and hasattr(solve_result, "ra_deg"):
        info_text = (
            f"Plate Solve: SUCCESS\n"
            f"\n"
            f"RA:  {solve_result.ra_deg:.4f}°\n"
            f"Dec: {solve_result.dec_deg:+.4f}°\n"
            f"Roll: {solve_result.roll_deg:.2f}°\n"
            f"FOV:  {solve_result.fov_deg:.2f}°\n"
            f"\n"
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
    print(f"Saved: {output_path}")
