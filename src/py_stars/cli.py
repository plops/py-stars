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
from py_stars.ephemeris import query_solar_system_ephemerides
from py_stars.exif import compute_camera_fov, get_gps_info, parse_exif
from py_stars.heic_loader import get_image_info, load_heic_as_uint8
from py_stars.plate_solver import (
    format_result,
    get_or_create_database,
    solve_heic_photo,
    solve_image,
)
from py_stars.satellites import (
    download_tle_group,
    match_satellites_with_centroids,
    parse_tle_data,
    query_satellites_in_fov,
)
from py_stars.star_detector import extract_centroids_tetra3
from py_stars.visualizer import (
    create_summary_image,
    ensure_output_dir,
    plot_cross_match_diagnostics,
    plot_ephemeris_and_dso_overlay,
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
    exp_time = exif.get("Exif", {}).get("ExposureTime") or exif.get("ExposureTime")

    print(f"Camera:     {make} {model}")
    print(f"Lens:       {lens}")
    print(f"Focal (35): {focal_35} mm (physical: {focal} mm)")
    if exp_time:
        print(f"Exposure:   {exp_time} s")

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
    """Solve one or more HEIC star photos, match catalog stars, planets, DSOs, and satellites."""
    db = get_or_create_database(args.database) if args.database else get_or_create_database()
    output_dir = ensure_output_dir(args.output_dir)

    camera_model = None
    if args.model_file:
        camera_model = load_camera_model(args.model_file)
    elif args.distortion:
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
            query_ephemeris=not args.no_ephem,
            query_dso=not args.no_dso,
            query_satellites=args.satellites,
            satellite_tle_source=args.tle,
            exposure_seconds=args.exposure,
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

        # Display Solar System Ephemeris in FOV
        planets_in_fov = result.get("planets_in_fov", [])
        if planets_in_fov:
            print("\n--- Solar System Bodies in FOV ---")
            for p in planets_in_fov:
                mag_s = f"{p.estimated_magnitude:+.1f} mag" if p.estimated_magnitude else "N/A"
                phase_s = (
                    f", {p.phase_fraction * 100.0:.0f}% illuminated"
                    if p.phase_fraction is not None
                    else ""
                )
                print(
                    f"  ★ {p.name:8s}: RA={p.ra_hms}, Dec={p.dec_dms}, "
                    f"Alt={p.alt_deg:+5.1f}°, Mag={mag_s}{phase_s}"
                )

        # Display Deep Sky Objects in FOV
        dsos_in_fov = result.get("dsos_in_fov", [])
        if dsos_in_fov:
            print("\n--- Deep Sky Objects (DSOs) in FOV ---")
            for p_dso in dsos_in_fov:
                dso = p_dso.dso
                name_s = f"({dso.name})" if dso.name else ""
                print(
                    f"  🌌 {dso.id:7s} {dso.obj_type:18s} {name_s:28s} "
                    f"{dso.magnitude:4.1f} mag  [{dso.constellation}]"
                )

        # Display Satellites in FOV & Matches
        sat_res = result.get("satellite_result")
        if sat_res and sat_res.passes:
            print(
                f"\n--- Satellites in FOV (Exposure: {sat_res.passes[0].exposure_seconds:.1f}s) ---"
            )
            print(f"  Total Tracked in FOV: {len(sat_res.passes)}")
            for sat_pass in sat_res.passes:
                streak_len_m = sat_pass.streak_length_arcmin
                streak_s = (
                    f", streak={sat_pass.streak_length_px:.1f}px ({streak_len_m:.1f}')"
                    if sat_pass.streak_length_px > 0
                    else ""
                )
                sunlit_s = "Sunlit" if sat_pass.is_sunlit else "Eclipsed"
                print(
                    f"  🛰 {sat_pass.name} [NORAD #{sat_pass.norad_cat_id}]: "
                    f"Alt={sat_pass.mid_alt_deg:.1f}°, Range={sat_pass.mid_range_km:.0f}km "
                    f"({sunlit_s}{streak_s})"
                )

            matches = result.get("satellite_matches", [])
            if matches:
                print(f"\n  Matched Detections with Satellites: {len(matches)}")
                for m in matches:
                    print(
                        f"    -> Matched {m.satellite_pass.name} with centroid #{m.centroid_idx} "
                        f'(residual: {m.min_distance_px:.2f} px / {m.min_distance_arcsec:.1f}")'
                    )

        # Generate diagnostic and ephemeris plots
        if args.plot and solve_res:
            gray = load_heic_as_uint8(f)

            if cm:
                diag_path = os.path.join(output_dir, f"{base}_diagnostics.png")
                plot_cross_match_diagnostics(
                    gray,
                    solve_res,
                    cm,
                    diag_path,
                    title=f"Astrometric & Completeness Diagnostics – {base}",
                )

            # Generate overlay if planets, DSOs, or satellites are in FOV
            if planets_in_fov or dsos_in_fov or (sat_res and sat_res.passes):
                overlay_path = os.path.join(output_dir, f"{base}_ephemeris_overlay.png")
                plot_ephemeris_and_dso_overlay(
                    image=gray,
                    solve_result=solve_res,
                    planets=planets_in_fov,
                    dsos=dsos_in_fov,
                    satellites=sat_res.passes if sat_res else None,
                    centroids=result["centroids"],
                    output_path=overlay_path,
                    title=f"Planets, DSOs & Satellites Overlay – {base}",
                )
            elif not cm:
                summary_path = os.path.join(output_dir, f"{base}_summary.png")
                create_summary_image(gray, result["centroids"], solve_res, summary_path)


def cmd_ephem(args: argparse.Namespace) -> None:
    """Query ephemerides for planets, Moon, Sun, and DSOs for an image or observation."""
    filepath = args.image
    if not os.path.exists(filepath):
        print(f"Error: File not found: {filepath}", file=sys.stderr)
        sys.exit(1)

    exif = parse_exif(filepath)
    gps = get_gps_info(exif)

    if not gps or gps.get("latitude_deg") is None or gps.get("utc_datetime") is None:
        print(
            "Error: Image does not contain valid GPS latitude and UTC timestamp in EXIF.",
            file=sys.stderr,
        )
        sys.exit(1)

    lat = gps["latitude_deg"]
    lon = gps["longitude_deg"]
    alt = gps.get("altitude_m", 0.0)
    utc_dt = gps["utc_datetime"]

    print("=" * 70)
    print(f"  Ephemerides & Deep Sky Objects: {os.path.basename(filepath)}")
    print("=" * 70)
    print(f"Observer: {lat:.6f}° N, {lon:.6f}° E, Alt: {alt:.1f} m")
    print(f"UTC Time: {utc_dt.isoformat()}")

    # Plate solve image if possible
    db = get_or_create_database(args.database) if args.database else get_or_create_database()
    solve_data = solve_heic_photo(
        filepath=filepath,
        db=db,
        query_ephemeris=True,
        query_dso=True,
        query_satellites=False,
    )
    solve_res = solve_data["solve_result"]
    gray = load_heic_as_uint8(filepath)
    h, w = gray.shape

    if solve_res:
        print(
            f"\nPlate Solve: RA={solve_res.ra_deg:.4f}°, "
            f"Dec={solve_res.dec_deg:+.4f}°, FOV={solve_res.fov_deg:.2f}°"
        )
    else:
        print("\nPlate Solve: None / Unsolved (calculating all-sky topocentric positions)")

    # Query Solar System Ephemerides
    ephem_res = solve_data["ephemeris_result"] or query_solar_system_ephemerides(
        utc_dt=utc_dt,
        lat_deg=lat,
        lon_deg=lon,
        alt_m=alt,
        solve_result=solve_res if solve_res else None,
        image_width=w,
        image_height=h,
    )

    print("\n--- Solar System Bodies (All-Sky Topocentric) ---")
    print(
        f"{'Body':10s} | {'RA (App)':14s} | {'Dec':14s} | {'Alt':7s} | "
        f"{'Az':7s} | {'Mag':6s} | {'Phase':6s} | {'In FOV':6s}"
    )
    print("-" * 80)
    for b in ephem_res.bodies:
        mag_s = f"{b.estimated_magnitude:+.1f}" if b.estimated_magnitude is not None else "  -  "
        phase_s = f"{b.phase_fraction * 100.0:4.0f}%" if b.phase_fraction is not None else "  -  "
        fov_s = "YES ★" if b.is_in_fov else ("(up)" if b.is_above_horizon else "down")
        print(
            f"{b.name:10s} | {b.ra_hms:14s} | {b.dec_dms:14s} | {b.alt_deg:+6.1f}° | "
            f"{b.az_deg:6.1f}° | {mag_s:6s} | {phase_s:6s} | {fov_s:6s}"
        )

    # Query DSOs
    dsos = solve_data["dsos_in_fov"]
    if solve_res:
        print(f"\n--- Deep Sky Objects in Camera FOV ({len(dsos)} objects) ---")
        if dsos:
            for p_dso in dsos:
                dso = p_dso.dso
                name_s = f"({dso.name})" if dso.name else ""
                print(
                    f"  🌌 {dso.id:6s} | {dso.obj_type:18s} | {name_s:24s} | "
                    f"{dso.magnitude:4.1f} mag | ({p_dso.image_x:6.1f} px, {p_dso.image_y:6.1f} px)"
                )
        else:
            print("  No Messier or bright NGC objects located inside this camera field of view.")

    # Save plot if requested
    if args.plot and solve_res:
        output_dir = ensure_output_dir(args.output_dir)
        base = os.path.splitext(os.path.basename(filepath))[0]
        out_path = os.path.join(output_dir, f"{base}_ephem_dso.png")
        plot_ephemeris_and_dso_overlay(
            image=gray,
            solve_result=solve_res,
            planets=ephem_res.bodies_in_fov,
            dsos=dsos,
            centroids=solve_data["centroids"],
            output_path=out_path,
            title=f"Planets & DSOs – {base}",
        )


def cmd_satellites(args: argparse.Namespace) -> None:
    """Propagate satellite orbits via SGP4, find satellites in FOV, and correlate streaks."""
    filepath = args.image
    if not os.path.exists(filepath):
        print(f"Error: File not found: {filepath}", file=sys.stderr)
        sys.exit(1)

    exif = parse_exif(filepath)
    gps = get_gps_info(exif)

    if not gps or gps.get("latitude_deg") is None or gps.get("utc_datetime") is None:
        print(
            "Error: Image does not contain valid GPS latitude and UTC timestamp in EXIF.",
            file=sys.stderr,
        )
        sys.exit(1)

    lat = gps["latitude_deg"]
    lon = gps["longitude_deg"]
    alt = gps.get("altitude_m", 0.0)
    utc_dt = gps["utc_datetime"]

    # Exposure time
    exp_time = args.exposure
    if exp_time is None:
        exif_sub = exif.get("Exif", {})
        raw_exp = exif_sub.get("ExposureTime") or exif.get("ExposureTime")
        exp_time = float(raw_exp) if raw_exp is not None else 1.0

    print("=" * 70)
    print(f"  Satellite Orbit Propagation (SGP4): {os.path.basename(filepath)}")
    print("=" * 70)
    print(f"Observer: {lat:.6f}° N, {lon:.6f}° E, Alt: {alt:.1f} m")
    print(f"UTC Time: {utc_dt.isoformat()}")
    print(f"Exposure: {exp_time:.2f} s")

    # Load TLEs
    print(f"\nLoading TLE dataset: '{args.tle}'...")
    tle_path = download_tle_group(group=args.tle, force_download=args.download)
    sats = parse_tle_data(tle_path)
    print(f"Loaded {len(sats)} satellite elements from {os.path.basename(tle_path)}.")

    # Plate solve image
    db = get_or_create_database(args.database) if args.database else get_or_create_database()
    solve_data = solve_heic_photo(
        filepath=filepath,
        db=db,
        query_ephemeris=False,
        query_dso=False,
        query_satellites=False,
    )
    solve_res = solve_data["solve_result"]
    gray = load_heic_as_uint8(filepath)
    h, w = gray.shape

    if not solve_res:
        print(
            "Warning: Plate solve failed for image; proceeding with all-sky propagation.",
            file=sys.stderr,
        )

    sat_res = query_satellites_in_fov(
        satellites=sats,
        lat_deg=lat,
        lon_deg=lon,
        alt_m=alt,
        utc_dt=utc_dt,
        solve_result=solve_res,
        image_width=w,
        image_height=h,
        exposure_seconds=exp_time,
        only_sunlit=args.sunlit_only,
    )

    print(f"\nTotal satellites propagated:  {sat_res.total_propagated}")
    print(f"Satellites above horizon:     {sat_res.above_horizon_count}")
    print(f"Satellites inside camera FOV: {sat_res.in_fov_count}")

    if sat_res.passes:
        print("\n--- Satellites in Field of View ---")
        for sat_pass in sat_res.passes:
            streak_s = (
                f", streak={sat_pass.streak_length_px:.1f}px ({sat_pass.streak_length_arcmin:.1f}')"
                if sat_pass.streak_length_px > 0
                else ""
            )
            sunlit_s = "Sunlit" if sat_pass.is_sunlit else "In Shadow"
            print(
                f"  🛰 {sat_pass.name} [NORAD #{sat_pass.norad_cat_id}]: "
                f"Alt={sat_pass.mid_alt_deg:.1f}°, Range={sat_pass.mid_range_km:.0f}km "
                f"({sunlit_s}{streak_s})"
            )

        # Correlation with detected image centroids
        centroids = solve_data["centroids"]
        if solve_res and centroids:
            matches = match_satellites_with_centroids(
                satellite_passes=sat_res.passes,
                centroids=centroids,
                image_width=w,
                image_height=h,
                solve_result=solve_res,
            )
            print(f"\n--- Satellite Streak / Point Matches ({len(matches)}) ---")
            if matches:
                for m in matches:
                    type_s = "streak" if m.is_streak_match else "point"
                    dist_s = f'{m.min_distance_px:.2f} px / {m.min_distance_arcsec:.1f}"'
                    print(
                        f"  -> Matched {m.satellite_pass.name} with centroid #{m.centroid_idx} "
                        f"({type_s}, distance: {dist_s})"
                    )
            else:
                print("  No detected stars/streaks closely matched the propagated satellite paths.")

    # Save plot
    if args.plot and solve_res:
        output_dir = ensure_output_dir(args.output_dir)
        base = os.path.splitext(os.path.basename(filepath))[0]
        out_path = os.path.join(output_dir, f"{base}_satellites.png")
        plot_ephemeris_and_dso_overlay(
            image=gray,
            solve_result=solve_res,
            satellites=sat_res.passes,
            centroids=solve_data["centroids"],
            output_path=out_path,
            title=f"Satellite Orbits & Streaks – {base}",
        )


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
        description=(
            "Plate solving, distortion/refraction correction, ephemerides, DSOs, and satellites."
        ),
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
        "solve", help="Plate solve image, match catalog stars, planets, DSOs, and satellites."
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
        "--no-ephem", action="store_true", help="Disable planet & Moon ephemeris querying."
    )
    p_solve.add_argument(
        "--no-dso", action="store_true", help="Disable Deep Sky Object (Messier/NGC) querying."
    )
    p_solve.add_argument(
        "--satellites",
        action="store_true",
        help="Enable SGP4 satellite orbit tracking & streak matching.",
    )
    p_solve.add_argument(
        "--tle",
        default="visual",
        help="TLE dataset ('visual', 'stations', 'starlink', 'active', or path).",
    )
    p_solve.add_argument(
        "--exposure",
        type=float,
        help="Exposure duration in seconds (defaults to EXIF ExposureTime).",
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

    # Subcommand: ephem
    p_ephem = subparsers.add_parser(
        "ephem", help="Query ephemerides for planets, Moon, Sun, and DSOs for an image."
    )
    p_ephem.add_argument("image", help="Path to HEIC image with GPS/UTC EXIF.")
    p_ephem.add_argument("--database", help="Path to tetra3rs database.")
    p_ephem.add_argument("--output-dir", default="output", help="Directory for output images.")
    p_ephem.add_argument(
        "--plot", action="store_true", default=True, help="Save ephemeris & DSO overlay plot."
    )
    p_ephem.set_defaults(func=cmd_ephem)

    # Subcommand: satellites
    p_sat = subparsers.add_parser(
        "satellites",
        help="Propagate satellite orbits (SGP4), find satellites in FOV, and correlate streaks.",
    )
    p_sat.add_argument("image", help="Path to HEIC image with GPS/UTC EXIF.")
    p_sat.add_argument(
        "--tle",
        default="visual",
        help="TLE group ('visual', 'stations', 'starlink', 'active') or file path.",
    )
    p_sat.add_argument(
        "--download", action="store_true", help="Force re-downloading TLEs from CelesTrak."
    )
    p_sat.add_argument(
        "--exposure", type=float, help="Exposure time in seconds (defaults to EXIF ExposureTime)."
    )
    p_sat.add_argument(
        "--sunlit-only", action="store_true", help="Only include satellites illuminated by the Sun."
    )
    p_sat.add_argument("--database", help="Path to tetra3rs database.")
    p_sat.add_argument("--output-dir", default="output", help="Directory for output images.")
    p_sat.add_argument(
        "--plot", action="store_true", default=True, help="Save satellite trajectory plot."
    )
    p_sat.set_defaults(func=cmd_satellites)

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
