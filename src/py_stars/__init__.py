"""py-stars: Plate solving, camera distortion & refraction, ephemerides, DSOs & satellites."""

__version__ = "0.3.0"

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
from py_stars.dso import (
    FULL_DSO_CATALOG,
    MESSIER_CATALOG,
    DeepSkyObject,
    ProjectedDSO,
    find_dso_by_name,
    get_all_dsos,
    project_dsos_to_image,
)
from py_stars.ephemeris import (
    EphemerisObservationResult,
    SolarSystemBodyPosition,
    estimate_planet_magnitude,
    get_ephemeris_context,
    query_solar_system_ephemerides,
)
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
from py_stars.satellites import (
    SatelliteMatch,
    SatelliteMatchResult,
    SatellitePass,
    SatelliteWaypoint,
    download_tle_group,
    match_satellites_with_centroids,
    parse_tle_data,
    propagate_satellite_trajectory,
    query_satellites_in_fov,
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
    plot_ephemeris_and_dso_overlay,
    plot_star_brightnesses,
)

__all__ = [
    "CrossMatchResult",
    "DeepSkyObject",
    "EphemerisObservationResult",
    "FULL_DSO_CATALOG",
    "LimitingMagnitudeReport",
    "MESSIER_CATALOG",
    "MatchedStarPair",
    "ProjectedDSO",
    "SatelliteMatch",
    "SatelliteMatchResult",
    "SatellitePass",
    "SatelliteWaypoint",
    "SolarSystemBodyPosition",
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
    "download_tle_group",
    "ensure_output_dir",
    "estimate_planet_magnitude",
    "extract_centroids_tetra3",
    "find_dso_by_name",
    "fit_instrumental_photometry",
    "format_result",
    "generate_database",
    "get_all_dsos",
    "get_default_camera_model",
    "get_ephemeris_context",
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
    "match_satellites_with_centroids",
    "parse_exif",
    "parse_tle_data",
    "plot_cross_match_diagnostics",
    "plot_detected_stars",
    "plot_ephemeris_and_dso_overlay",
    "plot_star_brightnesses",
    "preprocess_image",
    "project_dsos_to_image",
    "propagate_satellite_trajectory",
    "query_satellites_in_fov",
    "query_solar_system_ephemerides",
    "radec_to_altaz",
    "save_camera_model",
    "solve_heic_photo",
    "solve_image",
    "utc_to_gmst_deg",
]
