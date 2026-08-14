"""py-stars: Detect stars, plate solve, and analyze distortion & refraction."""

__version__ = "0.2.0"

from py_stars.astrometry import (
    altaz_to_radec,
    gmst_to_lst_deg,
    radec_to_altaz,
    utc_to_gmst_deg,
)
from py_stars.calibration import (
    calibrate_camera_from_solves,
    get_default_camera_model,
    load_camera_model,
    save_camera_model,
)
from py_stars.cli import main
from py_stars.exif import (
    compute_camera_fov,
    get_gps_info,
    parse_exif,
)
from py_stars.heic_loader import (
    get_image_info,
    load_heic,
    load_heic_as_gray,
    load_heic_as_uint8,
)
from py_stars.plate_solver import (
    format_result,
    generate_database,
    get_or_create_database,
    load_database,
    solve_heic_photo,
    solve_image,
)
from py_stars.refraction import (
    apply_refraction_to_catalog_stars,
    apply_refraction_to_radec,
    atmospheric_refraction_arcmin,
    barometric_pressure_hpa,
)
from py_stars.star_detector import (
    centroids_to_array,
    detect_stars_opencv,
    extract_centroids_tetra3,
    preprocess_image,
)
from py_stars.star_matching import (
    CrossMatchResult,
    LimitingMagnitudeReport,
    MatchedStarPair,
    calculate_limiting_magnitude,
    cross_match_stars,
    fit_instrumental_photometry,
)
from py_stars.visualizer import (
    create_summary_image,
    ensure_output_dir,
    plot_cross_match_diagnostics,
    plot_detected_stars,
    plot_star_brightnesses,
)

__all__ = [
    "CrossMatchResult",
    "LimitingMagnitudeReport",
    "MatchedStarPair",
    "altaz_to_radec",
    "apply_refraction_to_catalog_stars",
    "apply_refraction_to_radec",
    "atmospheric_refraction_arcmin",
    "barometric_pressure_hpa",
    "calculate_limiting_magnitude",
    "calibrate_camera_from_solves",
    "centroids_to_array",
    "compute_camera_fov",
    "create_summary_image",
    "cross_match_stars",
    "detect_stars_opencv",
    "ensure_output_dir",
    "extract_centroids_tetra3",
    "fit_instrumental_photometry",
    "format_result",
    "generate_database",
    "get_default_camera_model",
    "get_gps_info",
    "get_image_info",
    "get_or_create_database",
    "gmst_to_lst_deg",
    "load_camera_model",
    "load_database",
    "load_heic",
    "load_heic_as_gray",
    "load_heic_as_uint8",
    "main",
    "parse_exif",
    "plot_cross_match_diagnostics",
    "plot_detected_stars",
    "plot_star_brightnesses",
    "preprocess_image",
    "radec_to_altaz",
    "save_camera_model",
    "solve_heic_photo",
    "solve_image",
    "utc_to_gmst_deg",
]
