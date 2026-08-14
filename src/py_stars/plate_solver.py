"""Plate solving for iPhone star photos using tetra3rs.

Determines where in the sky the camera is pointing by matching detected
star patterns against the Gaia catalog.
"""

import os

import tetra3rs

# iPhone 11 Wide camera parameters
IPHONE11_HFOV = 71.5  # degrees, horizontal field of view
IPHONE11_VFOV = 56.8  # degrees, vertical field of view
IPHONE11_FOCAL_LENGTH_EQUIV = 26  # mm equivalent focal length

# Default database path
DEFAULT_DB_PATH = os.path.join(os.path.dirname(__file__), "data", "iphone_wide.bin")


def generate_database(
    save_path: str = DEFAULT_DB_PATH,
    max_fov_deg: float = 80.0,
    min_fov_deg: float = 50.0,
    star_max_magnitude: float = 7.0,
) -> tetra3rs.SolverDatabase:
    """Generate a star pattern database optimized for iPhone wide cameras.

    This takes a few minutes on first run. The database is saved to disk
    and can be reloaded later with load_database().

    Args:
        save_path: Where to save the database file.
        max_fov_deg: Maximum field of view in degrees.
        min_fov_deg: Minimum field of view in degrees.
        star_max_magnitude: Faintest star to include.

    Returns:
        The generated SolverDatabase.
    """
    print(f"Generating database: FOV={min_fov_deg}°-{max_fov_deg}°, mag<={star_max_magnitude}")
    print("This may take a few minutes...")

    db = tetra3rs.SolverDatabase.generate_from_gaia(
        max_fov_deg=max_fov_deg,
        min_fov_deg=min_fov_deg,
        star_max_magnitude=star_max_magnitude,
    )

    # Ensure directory exists
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
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
        raise FileNotFoundError(
            f"Database not found: {path}. Run generate_database() first to create one."
        )
    return tetra3rs.SolverDatabase.load_from_file(path)


def get_or_create_database(path: str = DEFAULT_DB_PATH) -> tetra3rs.SolverDatabase:
    """Load existing database or generate a new one.

    Args:
        path: Path to the database file.

    Returns:
        SolverDatabase (loaded or freshly generated).
    """
    if os.path.exists(path):
        print(f"Loading existing database: {path}")
        return load_database(path)
    else:
        print(f"No database found at {path}, generating...")
        return generate_database(save_path=path)


def solve_image(
    db: tetra3rs.SolverDatabase,
    centroids: list,
    image_width: int,
    image_height: int,
    fov_estimate_deg: float = IPHONE11_HFOV,
    fov_max_error_deg: float = 10.0,
    solve_timeout_ms: int = 5000,
) -> tetra3rs.SolveResult | tetra3rs.SolveFailure:
    """Run plate solving on extracted centroids.

    Args:
        db: The solver database.
        centroids: List of tetra3rs.Centroid objects or Nx2/Nx3 numpy array.
        image_width: Image width in pixels.
        image_height: Image height in pixels.
        fov_estimate_deg: Estimated horizontal FOV in degrees.
        fov_max_error_deg: Maximum FOV error tolerance.
        solve_timeout_ms: Timeout in milliseconds.

    Returns:
        SolveResult on success, SolveFailure on failure.
    """
    result = db.solve_from_centroids(
        centroids,
        fov_estimate_deg=fov_estimate_deg,
        image_width=image_width,
        image_height=image_height,
        fov_max_error_deg=fov_max_error_deg,
        solve_timeout_ms=solve_timeout_ms,
    )
    return result


def format_result(result) -> str:
    """Format a solve result as a human-readable string.

    Args:
        result: SolveResult or SolveFailure from solve_image().

    Returns:
        Formatted string with solve details.
    """
    if not result:  # SolveFailure is falsy
        return f"Solve FAILED: {result.status} (took {result.solve_time_ms:.1f}ms)"

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
    hours = deg / 15.0
    h = int(hours)
    m = int((hours - h) * 60)
    s = (hours - h - m / 60.0) * 3600
    return f"{h:02d}h {m:02d}m {s:05.2f}s"


def _deg_to_dms(deg: float) -> str:
    """Convert degrees to degrees:arcminutes:arcseconds format (for Dec)."""
    sign = "+" if deg >= 0 else "-"
    deg = abs(deg)
    d = int(deg)
    m = int((deg - d) * 60)
    s = (deg - d - m / 60.0) * 3600
    return f"{sign}{d:02d}° {m:02d}' {s:05.2f}\""
