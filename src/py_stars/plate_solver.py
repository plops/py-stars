"""Plate solving for star photos using tetra3rs and Gaia DR3.

Determines celestial camera pointing (RA, Dec, Roll) and matches detected
stars against the star catalog. Supports dynamic EXIF-derived FOV, camera
distortion models, and atmospheric refraction.
"""

import os
from typing import Any

import numpy as np
import tetra3rs

from py_stars.calibration import get_default_camera_model
from py_stars.exif import compute_camera_fov, get_gps_info, parse_exif
from py_stars.heic_loader import load_heic_as_uint8
from py_stars.star_detector import extract_centroids_tetra3
from py_stars.star_matching import CrossMatchResult, cross_match_stars

# Dynamic default database path resolution
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_DB_PATH = os.path.join(PROJECT_ROOT, "data", "iphone_wide.bin")

# iPhone 11 reference constants (for legacy fallback/reference)
IPHONE11_HFOV = 71.5
IPHONE11_VFOV = 56.8
IPHONE11_FOCAL_LENGTH_EQUIV = 26


def generate_database(
    save_path: str = DEFAULT_DB_PATH,
    max_fov_deg: float = 85.0,
    min_fov_deg: float = 45.0,
    star_max_magnitude: float = 7.0,
) -> tetra3rs.SolverDatabase:
    """Generate a star pattern database optimized for wide-field smartphone cameras.

    Args:
        save_path: Where to save the database file.
        max_fov_deg: Maximum field of view in degrees.
        min_fov_deg: Minimum field of view in degrees.
        star_max_magnitude: Faintest star to include in catalog patterns.

    Returns:
        The generated SolverDatabase.
    """
    print(f"Generating database: FOV={min_fov_deg}°-{max_fov_deg}°, mag<={star_max_magnitude}")
    print("This may take a few seconds...")

    db = tetra3rs.SolverDatabase.generate_from_gaia(
        max_fov_deg=max_fov_deg,
        min_fov_deg=min_fov_deg,
        star_max_magnitude=star_max_magnitude,
    )

    os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)
    db.save_to_file(save_path)
    print(f"Database saved to: {save_path}")
    return db


def load_database(path: str = DEFAULT_DB_PATH) -> tetra3rs.SolverDatabase:
    """Load a previously generated database.

    Args:
        path: Path to the database file.

    Returns:
        Loaded SolverDatabase.

    Raises:
        FileNotFoundError: If no database exists at the given path.
    """
    if not os.path.exists(path):
        # Also check fallback locations
        alt_path = os.path.join(os.path.dirname(__file__), "data", "iphone_wide.bin")
        if os.path.exists(alt_path):
            path = alt_path
        else:
            raise FileNotFoundError(
                f"Database not found: {path}. Run generate_database() first to create one."
            )
    return tetra3rs.SolverDatabase.load_from_file(path)


def get_or_create_database(path: str = DEFAULT_DB_PATH) -> tetra3rs.SolverDatabase:
    """Load existing database or generate a new one if missing.

    Args:
        path: Path to the database file.

    Returns:
        SolverDatabase (loaded or freshly generated).
    """
    if os.path.exists(path):
        return load_database(path)
    alt_path = os.path.join(os.path.dirname(__file__), "data", "iphone_wide.bin")
    if os.path.exists(alt_path):
        return load_database(alt_path)

    print(f"No database found at {path}, generating...")
    return generate_database(save_path=path)


def solve_image(
    db: tetra3rs.SolverDatabase,
    centroids: list[Any] | np.ndarray,
    image_width: int,
    image_height: int,
    fov_estimate_deg: float | None = None,
    fov_max_error_deg: float = 12.0,
    camera_model: tetra3rs.CameraModel | None = None,
    solve_timeout_ms: int = 5000,
) -> tetra3rs.SolveResult | tetra3rs.SolveFailure:
    """Run plate solving on extracted centroids.

    Does not require a hardcoded FOV if either `camera_model` or `fov_estimate_deg`
    is provided, or estimates dynamically from standard sensor geometry.

    Args:
        db: The solver database.
        centroids: List of tetra3rs.Centroid objects or Nx2/Nx3 numpy array.
        image_width: Image width in pixels.
        image_height: Image height in pixels.
        fov_estimate_deg: Estimated horizontal FOV in degrees (optional if camera_model provided).
        fov_max_error_deg: Maximum FOV error tolerance in degrees.
        camera_model: Optional calibrated CameraModel for distortion correction.
        solve_timeout_ms: Timeout in milliseconds.

    Returns:
        SolveResult on success, SolveFailure on failure.
    """
    if camera_model is not None:
        res = db.solve_from_centroids(
            centroids,
            camera_model=camera_model,
            solve_timeout_ms=solve_timeout_ms,
        )
        if res:
            return res

    # Fallback / standard pinhole solve with dynamic FOV
    fov_est = fov_estimate_deg if fov_estimate_deg is not None else 67.3
    return db.solve_from_centroids(
        centroids,
        fov_estimate_deg=fov_est,
        image_width=image_width,
        image_height=image_height,
        fov_max_error_deg=fov_max_error_deg,
        solve_timeout_ms=solve_timeout_ms,
    )


def solve_heic_photo(
    filepath: str,
    db: tetra3rs.SolverDatabase | None = None,
    camera_model: tetra3rs.CameraModel | None = None,
    use_distortion_correction: bool = True,
    distortion_model_type: str = "radial",
    apply_atmospheric_refraction: bool = True,
    max_centroids: int = 100,
    sigma_threshold: float = 10.0,
    max_match_radius_px: float = 12.0,
    roi: tuple[int, int, int, int] | None = None,
    auto_sky_crop: bool = True,
) -> dict[str, Any]:
    """Complete end-to-end processing of a HEIC star photo.

    Steps:
    1. Parse EXIF: focal length, dynamic FOV, GPS coordinates, timestamp, compass.
    2. Load image as grayscale uint8.
    3. Extract star centroids with sub-pixel fitting.
    4. Apply camera distortion model (radial/polynomial) if requested.
    5. Plate solve against Gaia catalog using dynamic EXIF FOV.
    6. Cross-match all catalog stars in FOV against image centroids.
    7. Apply atmospheric refraction correction using observer altitude & temperature.
    8. Perform limiting magnitude & detection completeness analysis.

    Args:
        filepath: Path to the HEIC photo.
        db: Optional loaded SolverDatabase. Loaded automatically if None.
        camera_model: Optional CameraModel object.
        use_distortion_correction: If True and camera_model is None, loads default model.
        distortion_model_type: "radial" or "polynomial".
        apply_atmospheric_refraction: If True, corrects for atmosphere when GPS is present.
        max_centroids: Maximum centroids to extract (default 100).
        sigma_threshold: Centroid detection threshold above background sigma.
        max_match_radius_px: Radius in pixels for catalog cross-matching.

    Returns:
        Dict with keys: filepath, exif, gps_info, computed_fov, centroids,
        solve_result, cross_match_result, camera_model.
    """
    if db is None:
        db = get_or_create_database()

    # 1. Parse EXIF & compute dynamic FOV
    exif = parse_exif(filepath)
    gps_info = get_gps_info(exif)

    # 2. Load image
    gray = load_heic_as_uint8(filepath)
    h, w = gray.shape

    hfov, vfov, dfov = compute_camera_fov(exif, image_width=w, image_height=h)

    # 3. Extract centroids (with optional ROI)
    extraction = extract_centroids_tetra3(
        gray, sigma_threshold=sigma_threshold, max_centroids=max_centroids, roi=roi
    )
    centroids = extraction.centroids

    # 4. Resolve camera model for distortion correction
    model_to_use = camera_model
    if model_to_use is None and use_distortion_correction:
        model_to_use = get_default_camera_model(model_type=distortion_model_type)

    # 5. Plate solve
    solve_result = solve_image(
        db=db,
        centroids=centroids,
        image_width=w,
        image_height=h,
        fov_estimate_deg=hfov,
        camera_model=model_to_use,
    )

    # Fallback to upper sky crop if initial solve fails and auto_sky_crop is enabled
    if not solve_result and auto_sky_crop and roi is None:
        sky_roi = (0, int(h * 0.45), 0, w)
        sky_extraction = extract_centroids_tetra3(
            gray, sigma_threshold=sigma_threshold, max_centroids=max_centroids, roi=sky_roi
        )
        if len(sky_extraction.centroids) >= 4:
            sky_solve = solve_image(
                db=db,
                centroids=sky_extraction.centroids,
                image_width=w,
                image_height=h,
                fov_estimate_deg=hfov,
                camera_model=model_to_use,
            )
            if sky_solve:
                solve_result = sky_solve
                centroids = sky_extraction.centroids
                extraction = sky_extraction

    # 6 & 7 & 8. Catalog cross-matching, refraction & limiting magnitude
    cross_match: CrossMatchResult | None = None
    if solve_result:
        cross_match = cross_match_stars(
            db=db,
            solve_result=solve_result,
            centroids=centroids,
            image_width=w,
            image_height=h,
            camera_model=model_to_use,
            max_match_radius_px=max_match_radius_px,
            gps_info=gps_info,
            apply_refraction=apply_atmospheric_refraction,
        )

    return {
        "filepath": filepath,
        "image_shape": (h, w),
        "exif": exif,
        "gps_info": gps_info,
        "computed_fov": {"hfov_deg": hfov, "vfov_deg": vfov, "dfov_deg": dfov},
        "centroids": centroids,
        "extraction_stats": {
            "background_mean": extraction.background_mean,
            "background_sigma": extraction.background_sigma,
            "threshold": extraction.threshold,
            "count": len(centroids),
        },
        "solve_result": solve_result,
        "cross_match_result": cross_match,
        "camera_model": model_to_use,
    }


def format_result(result: Any) -> str:
    """Format a solve result as a human-readable string.

    Args:
        result: SolveResult or SolveFailure from solve_image().

    Returns:
        Formatted string with solve details.
    """
    if not result:
        status = getattr(result, "status", "unknown")
        solve_time = getattr(result, "solve_time_ms", 0.0)
        return f"Solve FAILED: {status} (took {solve_time:.1f}ms)"

    lines = [
        "=== Plate Solve Result ===",
        f"  RA:        {result.ra_deg:.4f}° ({_deg_to_hms(result.ra_deg)})",
        f"  Dec:       {result.dec_deg:+.4f}°  ({_deg_to_dms(result.dec_deg)})",
        f"  Roll:      {result.roll_deg:.2f}°",
        f"  FOV:       {result.fov_deg:.2f}°",
        f"  Matches:   {result.num_matches}",
        f'  RMSE:      {result.rmse_arcsec:.2f}"',
        f"  Time:      {result.solve_time_ms:.1f}ms",
        f"  Prob:      {result.probability:.2e}",
    ]
    return "\n".join(lines)


def _deg_to_hms(deg: float) -> str:
    """Convert degrees to hours:minutes:seconds format (for RA)."""
    hours = (deg % 360.0) / 15.0
    h = int(hours)
    m = int((hours - h) * 60)
    s = (hours - h - m / 60.0) * 3600
    return f"{h:02d}h {m:02d}m {s:05.2f}s"


def _deg_to_dms(deg: float) -> str:
    """Convert degrees to degrees:arcminutes:arcseconds format (for Dec)."""
    sign = "+" if deg >= 0 else "-"
    d_abs = abs(deg)
    d = int(d_abs)
    m = int((d_abs - d) * 60)
    s = (d_abs - d - m / 60.0) * 3600
    return f"{sign}{d:02d}° {m:02d}' {s:05.2f}\""
