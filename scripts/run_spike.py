#!/usr/bin/env python3
"""Spike script: End-to-end star detection and plate solving pipeline.

This script demonstrates the complete pipeline:
1. Load HEIC photo from iPhone
2. Convert to grayscale
3. Detect stars (extract centroids)
4. Plate solve (determine where the camera is pointing)
5. Visualize results

File paths are hardcoded for spike exploration.
"""

import glob
import os
import time

from py_stars.heic_loader import get_image_info, load_heic_as_uint8
from py_stars.plate_solver import (
    IPHONE11_HFOV,
    format_result,
    get_or_create_database,
    solve_image,
)
from py_stars.star_detector import (
    centroids_to_array,
    extract_centroids_tetra3,
)
from py_stars.visualizer import (
    create_summary_image,
    ensure_output_dir,
    plot_detected_stars,
    plot_star_brightnesses,
)

# ============================================================================
# Configuration – file paths for spike
# ============================================================================

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Candidate directories / files to search for HEIC images
CANDIDATE_PATHS = [
    "/home/kiel/Downloads/Stars/*.HEIC",
    "/home/kiel/Downloads/Stars/*.heic",
    "/workspace/src/*.HEIC",
    "/workspace/src/laserboard_kt/kt/*.HEIC",
]

# Output directory for generated images
OUTPUT_DIR = os.path.join(project_root, "output")

# Database path
DB_PATH = os.path.join(project_root, "data", "iphone_wide.bin")


def main():
    """Run the complete star detection and plate solving pipeline."""
    print("=" * 70)
    print("  py-stars: Star Detection & Plate Solving Spike")
    print("=" * 70)
    print()

    # ---- Step 0: Setup ----
    ensure_output_dir(OUTPUT_DIR)

    # ---- Step 1: Load database (generate if needed) ----
    print("[Step 1] Loading/generating star pattern database...")
    t0 = time.time()
    db = get_or_create_database(DB_PATH)
    print(f"  Database ready in {time.time() - t0:.1f}s")
    print()

    # Find all available HEIC files
    heic_files = []
    for pattern in CANDIDATE_PATHS:
        heic_files.extend(glob.glob(pattern))
    heic_files = sorted(list(set(heic_files)))

    if not heic_files:
        print("No HEIC files found in candidate paths.")
        return

    print(f"Found {len(heic_files)} HEIC files to process.")

    # ---- Step 2: Process each HEIC file ----
    for heic_path in heic_files:
        print(f"{'=' * 70}")
        print(f"  Processing: {os.path.basename(heic_path)}")
        print(f"{'=' * 70}")

        if not os.path.exists(heic_path):
            print(f"  SKIPPED: File not found: {heic_path}")
            continue

        # ---- Step 2a: Load image ----
        print("\n[Step 2a] Loading HEIC image...")
        info = get_image_info(heic_path)
        print(f"  Size: {info['width']} x {info['height']}")
        print(f"  Mode: {info['mode']}")

        gray = load_heic_as_uint8(heic_path)
        print(f"  Grayscale shape: {gray.shape}")
        print(f"  Min/Max pixel values: {gray.min()} / {gray.max()}")

        # ---- Step 2b: Extract centroids ----
        print("\n[Step 2b] Extracting star centroids...")
        t0 = time.time()
        extraction = extract_centroids_tetra3(gray, sigma_threshold=10.0, max_centroids=100)
        extraction_time = time.time() - t0

        centroids = extraction.centroids
        print(f"  Found {len(centroids)} centroids in {extraction_time:.2f}s")
        bg_mean = extraction.background_mean
        bg_sigma = extraction.background_sigma
        print(f"  Background: mean={bg_mean:.1f}, sigma={bg_sigma:.1f}")
        print(f"  Detection threshold: {extraction.threshold:.1f}")

        if centroids:
            arr = centroids_to_array(centroids)
            b_star = f"({arr[0, 0]:.1f}, {arr[0, 1]:.1f})"
            print(f"  Brightest star: brightness={arr[0, 2]:.0f} at {b_star}")
            print(f"  Faintest star:  brightness={arr[-1, 2]:.0f}")

        # ---- Step 2c: Plate solve ----
        print("\n[Step 2c] Plate solving...")
        t0 = time.time()

        if len(centroids) < 4:
            print(f"  SKIPPED: Only {len(centroids)} centroids found (need >=4)")
            solve_result = None
        else:
            solve_result = solve_image(
                db=db,
                centroids=centroids,
                image_width=gray.shape[1],
                image_height=gray.shape[0],
                fov_estimate_deg=IPHONE11_HFOV,
            )
            solve_time = time.time() - t0
            print(f"  Solve completed in {solve_time:.2f}s")
            print()
            print(format_result(solve_result))

        # ---- Step 2d: Visualize ----
        print("\n[Step 2d] Creating visualizations...")
        basename = os.path.splitext(os.path.basename(heic_path))[0]

        # Plot detected stars
        plot_detected_stars(
            gray,
            centroids,
            os.path.join(OUTPUT_DIR, f"{basename}_stars.png"),
            title=f"Detected Stars - {basename}",
        )

        # Plot brightness distribution
        if centroids:
            plot_star_brightnesses(
                centroids,
                os.path.join(OUTPUT_DIR, f"{basename}_brightness.png"),
            )

        # Create summary image
        create_summary_image(
            gray,
            centroids,
            solve_result,
            os.path.join(OUTPUT_DIR, f"{basename}_summary.png"),
            title=f"Summary - {basename}",
        )

        print()

    print("\n" + "=" * 70)
    print("  Done! Check output/ directory for results.")
    print("=" * 70)


if __name__ == "__main__":
    main()
