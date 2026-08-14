"""Command-line interface for py-stars."""

import argparse
import glob
import os
import sys

from py_stars.calibration import (
    DEFAULT_POLY_MODEL_PATH,
    DEFAULT_RADIAL_MODEL_PATH,
    calibrate_camera_from_solves,
    load_camera_model,
    save_camera_model,
)
from py_stars.exif import compute_camera_fov, get_gps_info, parse_exif
from py_stars.heic_loader import get_image_info, load_heic_as_uint8
from py_stars.plate_solver import (
    format_result,
    get_or_create_database,
    solve_heic_photo,
    solve_image,
)
from py_stars.star_detector import extract_centroids_tetra3
from py_stars.visualizer import (
    create_summary_image,
    ensure_output_dir,
    plot_cross_match_diagnostics,
)


def cmd_info(args: argparse.Namespace) -> None:
    """Display image metadata, EXIF, GPS, and computed dynamic FOV."""
    filepath = args.image
    if not os.path.exists(filepath):
        print(f"Error: File not found: {filepath}", file=sys.stderr)
        sys.exit(1)

    print("=" * 60)
    print(f"  Image Metadata: {os.path.basename(filepath)}")
    print("=" * 60)

    info = get_image_info(filepath)
    print(f"Dimensions: {info['width']} x {info['height']}")
    print(f"Format:     {info['format']} ({info['mode']})")

    exif = parse_exif(filepath)
    make = exif.get("Make", "Unknown")
    model = exif.get("Model", "Unknown")
    lens = exif.get("Exif", {}).get("LensModel") or exif.get("LensModel", "Unknown")
    focal_35 = exif.get("Exif", {}).get("FocalLengthIn35mmFilm") or exif.get(
        "FocalLengthIn35mmFilm"
    )
    focal = exif.get("Exif", {}).get("FocalLength") or exif.get("FocalLength")

    print(f"Camera:     {make} {model}")
    print(f"Lens:       {lens}")
    print(f"Focal (35): {focal_35} mm (physical: {focal} mm)")

    hfov, vfov, dfov = compute_camera_fov(
        exif, image_width=info["width"], image_height=info["height"]
    )
    print(f"Computed FOV: HFOV = {hfov:.2f}°, VFOV = {vfov:.2f}°, DFOV = {dfov:.2f}°")

    gps = get_gps_info(exif)
    if gps:
        print("\nGPS Data:")
        print(f"  Latitude:   {gps['latitude_deg']:.6f}°")
        print(f"  Longitude:  {gps['longitude_deg']:.6f}°")
        print(f"  Altitude:   {gps['altitude_m']:.1f} m")
        if gps["utc_datetime"]:
            print(f"  UTC Time:   {gps['utc_datetime'].isoformat()}")
        if gps["compass_heading_deg"] is not None:
            print(f"  Heading:    {gps['compass_heading_deg']:.2f}°")
    else:
        print("\nGPS Data: None (no GPS tags found)")


def cmd_solve(args: argparse.Namespace) -> None:
    """Solve one or more HEIC star photos and run catalog matching."""
    db = get_or_create_database(args.database) if args.database else get_or_create_database()
    output_dir = ensure_output_dir(args.output_dir)

    camera_model = None
    if args.model_file:
        camera_model = load_camera_model(args.model_file)
    elif args.distortion:
        # Load default radial or poly model
        m_path = (
            DEFAULT_RADIAL_MODEL_PATH if args.distortion == "radial" else DEFAULT_POLY_MODEL_PATH
        )
        if os.path.exists(m_path):
            camera_model = load_camera_model(m_path)
            print(f"Loaded distortion model: {os.path.basename(m_path)}")

    # Expand glob if needed
    files = []
    for pattern in args.images:
        expanded = glob.glob(pattern)
        if expanded:
            files.extend(expanded)
        elif os.path.exists(pattern):
            files.append(pattern)

    files = sorted(list(set(files)))
    if not files:
        print(f"No image files matched: {args.images}", file=sys.stderr)
        sys.exit(1)

    print(f"Processing {len(files)} image(s)...")

    for f in files:
        base = os.path.splitext(os.path.basename(f))[0]
        print("\n" + "=" * 70)
        print(f"  Processing: {os.path.basename(f)}")
        print("=" * 70)

        roi = tuple(args.roi) if args.roi and len(args.roi) == 4 else None
        result = solve_heic_photo(
            filepath=f,
            db=db,
            camera_model=camera_model,
            use_distortion_correction=bool(args.distortion or args.model_file),
            distortion_model_type=args.distortion or "radial",
            apply_atmospheric_refraction=not args.no_refraction,
            max_centroids=args.max_centroids,
            sigma_threshold=args.sigma_threshold,
            roi=roi,
            auto_sky_crop=not args.no_auto_sky,
        )

        solve_res = result["solve_result"]
        print(format_result(solve_res))

        cm = result["cross_match_result"]
        if cm:
            print("\n--- Catalog Matching & Astrometric Accuracy ---")
            print(f"  Catalog Stars in FOV:  {cm.limiting_magnitude.total_catalog_in_frame}")
            mean_arc = cm.mean_residual_px * cm.pixel_scale_arcsec_per_px
            med_arc = cm.median_residual_px * cm.pixel_scale_arcsec_per_px
            print(f'  Mean Residual:         {cm.mean_residual_px:.2f} px ({mean_arc:.1f}")')
            print(f'  Median Residual:       {cm.median_residual_px:.2f} px ({med_arc:.1f}")')
            print(f'  Astrometric RMSE:      {cm.rmse_arcsec:.2f}" ({cm.rmse_px:.2f} px)')
            ref_status = "Enabled" if cm.applied_refraction else "Disabled / No GPS"
            dist_status = "Active" if cm.used_distortion_model else "Pinhole (uncalibrated)"
            print(f"  Atmospheric Refraction: {ref_status}")
            print(f"  Distortion Model:       {dist_status}")

            print("\n--- Limiting Magnitude & Star Detectability ---")
            lim = cm.limiting_magnitude
            print(
                f"  Brightest Star:        {lim.brightest_detected_magnitude:.2f} mag"
                if lim.brightest_detected_magnitude
                else "  N/A"
            )
            print(
                f"  Faintest Star:         {lim.faintest_detected_magnitude:.2f} mag"
                if lim.faintest_detected_magnitude
                else "  N/A"
            )
            if lim.mag_90_completeness:
                print(f"  90% Completeness Limit: {lim.mag_90_completeness:.2f} mag")
            if lim.mag_50_completeness:
                print(f"  50% Limiting Magnitude: {lim.mag_50_completeness:.2f} mag")

            print("\n  Detection by Magnitude:")
            for b in lim.mag_bins:
                if b.total_in_frame > 0:
                    pct = b.completeness_rate * 100.0
                    print(
                        f"    Mag [{b.mag_min:3.1f} - {b.mag_max:3.1f}]: "
                        f"{b.detected_count:2d} / {b.total_in_frame:2d} ({pct:5.1f}%)"
                    )

            if cm.photometry:
                zp = cm.photometry.zero_point
                sc = cm.photometry.photometric_scatter_mag
                print(f"\n  Photometry Zero-point:  {zp:.2f} mag (scatter σ = {sc:.2f} mag)")

            # Generate diagnostic plot
            if args.plot:
                gray = load_heic_as_uint8(f)
                diag_path = os.path.join(output_dir, f"{base}_diagnostics.png")
                plot_cross_match_diagnostics(
                    gray,
                    solve_res,
                    cm,
                    diag_path,
                    title=f"Astrometric & Completeness Diagnostics – {base}",
                )
        else:
            if args.plot and solve_res:
                gray = load_heic_as_uint8(f)
                summary_path = os.path.join(output_dir, f"{base}_summary.png")
                create_summary_image(gray, result["centroids"], solve_res, summary_path)


def cmd_calibrate(args: argparse.Namespace) -> None:
    """Calibrate camera distortion across multiple images."""
    db = get_or_create_database(args.database) if args.database else get_or_create_database()

    files = []
    for pattern in args.images:
        expanded = glob.glob(pattern)
        if expanded:
            files.extend(expanded)
        elif os.path.exists(pattern):
            files.append(pattern)

    files = sorted(list(set(files)))
    if len(files) < 2:
        print("Error: Multi-frame calibration requires at least 2 images.", file=sys.stderr)
        sys.exit(1)

    print(f"Solving {len(files)} images for camera calibration...")

    solve_results = []
    centroids_list = []
    w, h = 0, 0

    for f in files:
        gray = load_heic_as_uint8(f)
        h, w = gray.shape
        hfov, _, _ = compute_camera_fov(f, image_width=w, image_height=h)

        ext = extract_centroids_tetra3(
            gray, sigma_threshold=args.sigma_threshold, max_centroids=args.max_centroids
        )
        res = solve_image(db, ext.centroids, image_width=w, image_height=h, fov_estimate_deg=hfov)
        if res:
            solve_results.append(res)
            centroids_list.append(ext.centroids)
            fname = os.path.basename(f)
            print(f'  [Solved] {fname}: {res.num_matches} matches, RMSE={res.rmse_arcsec:.1f}"')
        else:
            print(f"  [Failed] {os.path.basename(f)}")

    if len(solve_results) < 2:
        print("Error: Could not solve enough images to fit camera calibration.", file=sys.stderr)
        sys.exit(1)

    print(f"\nFitting {args.model} distortion model across {len(solve_results)} images...")
    cal = calibrate_camera_from_solves(
        db=db,
        solve_results=solve_results,
        centroids_list=centroids_list,
        image_width=w,
        image_height=h,
        model=args.model,
        order=args.order,
    )

    cm_focal = cal.camera_model.focal_length_px
    cm_fov = cal.camera_model.fov_deg
    print(f"Focal length: {cm_focal:.2f} px (FOV = {cm_fov:.2f}°)")
    print(f"Optical center: {cal.camera_model.crpix}")

    out_path = args.output
    if not out_path:
        out_path = DEFAULT_RADIAL_MODEL_PATH if args.model == "radial" else DEFAULT_POLY_MODEL_PATH

    save_camera_model(cal.camera_model, out_path)
    print(f"Saved calibrated camera model to: {out_path}")


def main() -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="py-stars",
        description="Plate solving, distortion/refraction correction, and star detectability.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Subcommand: info
    p_info = subparsers.add_parser(
        "info", help="Inspect image EXIF metadata, GPS, and dynamic FOV."
    )
    p_info.add_argument("image", help="Path to HEIC image.")
    p_info.set_defaults(func=cmd_info)

    # Subcommand: solve
    p_solve = subparsers.add_parser(
        "solve", help="Plate solve image, match catalog stars, and analyze limiting magnitude."
    )
    p_solve.add_argument("images", nargs="+", help="HEIC image file(s) or glob pattern.")
    p_solve.add_argument(
        "--distortion",
        choices=["radial", "polynomial"],
        default="radial",
        help="Apply camera distortion model.",
    )
    p_solve.add_argument("--model-file", help="Path to custom CameraModel .bin file.")
    p_solve.add_argument(
        "--no-refraction", action="store_true", help="Disable atmospheric refraction correction."
    )
    p_solve.add_argument(
        "--max-centroids", type=int, default=100, help="Maximum centroids to extract (default 100)."
    )
    p_solve.add_argument(
        "--sigma-threshold",
        type=float,
        default=10.0,
        help="Detection threshold above background sigma (default 10.0).",
    )
    p_solve.add_argument("--database", help="Path to tetra3rs database file.")
    p_solve.add_argument(
        "--roi",
        nargs=4,
        type=int,
        metavar=("YMIN", "YMAX", "XMIN", "XMAX"),
        help="Region of interest pixel bounds.",
    )
    p_solve.add_argument(
        "--no-auto-sky", action="store_true", help="Disable automatic sky ROI fallback on failure."
    )
    p_solve.add_argument(
        "--output-dir", default="output", help="Directory for output images (default output/)."
    )
    p_solve.add_argument(
        "--plot", action="store_true", default=True, help="Save diagnostic visualization plots."
    )
    p_solve.set_defaults(func=cmd_solve)

    # Subcommand: calibrate
    p_cal = subparsers.add_parser(
        "calibrate", help="Calibrate camera distortion across multiple images."
    )
    p_cal.add_argument("images", nargs="+", help="HEIC image files for multi-frame calibration.")
    p_cal.add_argument(
        "--model", choices=["radial", "polynomial"], default="radial", help="Distortion model type."
    )
    p_cal.add_argument("--order", type=int, default=3, help="Polynomial order if model=polynomial.")
    p_cal.add_argument("--output", help="Destination path for .bin camera model.")
    p_cal.add_argument(
        "--max-centroids", type=int, default=80, help="Maximum centroids to extract."
    )
    p_cal.add_argument("--sigma-threshold", type=float, default=10.0, help="Centroid threshold.")
    p_cal.add_argument("--database", help="Path to tetra3rs database.")
    p_cal.set_defaults(func=cmd_calibrate)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
