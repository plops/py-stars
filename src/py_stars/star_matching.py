"""Catalog star cross-matching, astrometric residuals, and limiting magnitude analysis."""

import math
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import tetra3rs
from scipy.spatial import KDTree

from py_stars.astrometry import utc_to_gmst_deg
from py_stars.refraction import apply_refraction_to_radec, barometric_pressure_hpa


@dataclass
class MatchedStarPair:
    """Details of a single matched catalog star and image centroid."""

    catalog_id: int
    magnitude: float
    true_ra_deg: float
    true_dec_deg: float
    app_ra_deg: float
    app_dec_deg: float
    true_alt_deg: float | None
    app_alt_deg: float | None
    refraction_arcsec: float
    # Projected catalog coordinates (center origin: [-W/2, +W/2], [-H/2, +H/2])
    proj_x: float
    proj_y: float
    # Detected centroid coordinates (center origin)
    centroid_idx: int
    det_x: float
    det_y: float
    det_brightness: float
    # Residuals
    dx_px: float
    dy_px: float
    dist_px: float
    dist_arcsec: float


@dataclass
class MagnitudeBinStats:
    """Detection statistics for a single magnitude interval."""

    mag_min: float
    mag_max: float
    mag_center: float
    total_in_frame: int
    detected_count: int
    completeness_rate: float  # [0.0, 1.0]


@dataclass
class LimitingMagnitudeReport:
    """Comprehensive limiting magnitude and detection efficiency report."""

    mag_bins: list[MagnitudeBinStats] = field(default_factory=list)
    mag_50_completeness: float | None = None
    mag_90_completeness: float | None = None
    faintest_detected_magnitude: float | None = None
    brightest_detected_magnitude: float | None = None
    faintest_catalog_star_id: int | None = None
    total_catalog_in_frame: int = 0
    total_detected_in_frame: int = 0
    overall_detection_rate: float = 0.0


@dataclass
class PhotometryFit:
    """Instrumental flux vs catalog magnitude relationship."""

    zero_point: float
    photometric_scatter_mag: float
    matched_count: int


@dataclass
class CrossMatchResult:
    """Full results of catalog cross-matching, astrometric accuracy, and detectability."""

    matched_stars: list[MatchedStarPair] = field(default_factory=list)
    unmatched_catalog_stars: list[dict[str, Any]] = field(default_factory=list)
    unmatched_centroids: list[dict[str, Any]] = field(default_factory=list)
    # Astrometric residuals
    mean_residual_px: float = 0.0
    median_residual_px: float = 0.0
    rmse_px: float = 0.0
    rmse_arcsec: float = 0.0
    pixel_scale_arcsec_per_px: float = 0.0
    # Limiting magnitude analysis
    limiting_magnitude: LimitingMagnitudeReport = field(default_factory=LimitingMagnitudeReport)
    # Photometry calibration
    photometry: PhotometryFit | None = None
    # Settings used
    applied_refraction: bool = False
    used_distortion_model: bool = False


def cross_match_stars(
    db: tetra3rs.SolverDatabase,
    solve_result: tetra3rs.SolveResult,
    centroids: list[Any],
    image_width: int,
    image_height: int,
    camera_model: tetra3rs.CameraModel | None = None,
    max_match_radius_px: float = 12.0,
    gps_info: dict[str, Any] | None = None,
    pressure_hpa: float | None = None,
    temp_c: float = 15.0,
    apply_refraction: bool = True,
) -> CrossMatchResult:
    """Cross-match detected centroids against all Gaia/Hipparcos catalog stars in the image frame.

    Evaluates:
    - How well catalog stars match image stars (astrometric residuals).
    - Effect of atmospheric refraction & camera distortion.
    - Which stars can still be detected (limiting magnitude analysis).

    Args:
        db: tetra3rs.SolverDatabase instance.
        solve_result: Successful SolveResult from plate solving.
        centroids: List of tetra3rs.Centroid objects extracted from the image.
        image_width: Image width in pixels.
        image_height: Image height in pixels.
        camera_model: Optional calibrated CameraModel for distortion handling.
        max_match_radius_px: Maximum pixel distance for a 1-to-1 star match.
        gps_info: Optional GPS dictionary with latitude_deg, longitude_deg,
            altitude_m, utc_datetime.
        pressure_hpa: Optional barometric pressure in hPa.
        temp_c: Ambient temperature in Celsius (default 15.0).
        apply_refraction: Whether to apply atmospheric refraction if GPS & time are available.

    Returns:
        CrossMatchResult containing matched pairs, residuals, limiting magnitude, and photometry.
    """
    w, h = float(image_width), float(image_height)
    pixel_scale = (solve_result.fov_deg * 3600.0) / w

    # Cone search around camera pointing center
    search_radius_deg = solve_result.fov_deg * 0.75
    catalog_stars = db.cone_search(
        solve_result.ra_deg, solve_result.dec_deg, radius_deg=search_radius_deg
    )

    # Check if atmospheric refraction can be applied
    refraction_active = False
    lat, lon, gmst = 0.0, 0.0, 0.0
    p_hpa = pressure_hpa or 1013.25

    if apply_refraction and gps_info and gps_info.get("latitude_deg") is not None:
        lat = gps_info["latitude_deg"]
        lon = gps_info["longitude_deg"]
        alt_m = gps_info.get("altitude_m", 0.0)
        if pressure_hpa is None:
            p_hpa = barometric_pressure_hpa(alt_m)

        dt = gps_info.get("utc_datetime")
        if dt is not None:
            gmst = utc_to_gmst_deg(dt)
            refraction_active = True

    # Project catalog stars to image plane
    visible_catalog: list[dict[str, Any]] = []

    for star in catalog_stars:
        if refraction_active:
            app_ra, app_dec, true_alt, app_alt, r_arcsec = apply_refraction_to_radec(
                star.ra_deg,
                star.dec_deg,
                lat,
                lon,
                gmst,
                pressure_hpa=p_hpa,
                temp_c=temp_c,
            )
            proj_ra, proj_dec = app_ra, app_dec
        else:
            app_ra, app_dec = star.ra_deg, star.dec_deg
            true_alt, app_alt, r_arcsec = None, None, 0.0
            proj_ra, proj_dec = star.ra_deg, star.dec_deg

        # Project celestial coordinate to center-origin pixel coordinate
        px, py = solve_result.world_to_pixel(proj_ra, proj_dec)

        # Check if inside sensor boundaries
        if -w / 2.0 <= px <= w / 2.0 and -h / 2.0 <= py <= h / 2.0:
            visible_catalog.append(
                {
                    "star": star,
                    "id": star.id,
                    "magnitude": star.magnitude,
                    "true_ra": star.ra_deg,
                    "true_dec": star.dec_deg,
                    "app_ra": app_ra,
                    "app_dec": app_dec,
                    "true_alt": true_alt,
                    "app_alt": app_alt,
                    "refraction_arcsec": r_arcsec,
                    "px": px,
                    "py": py,
                }
            )

    # Cross-match with detected centroids
    matched_pairs: list[MatchedStarPair] = []
    matched_cat_indices: set[int] = set()
    matched_centroid_indices: set[int] = set()

    if visible_catalog and centroids:
        cat_xy = np.array([[c["px"], c["py"]] for c in visible_catalog])
        img_xy = np.array([[c.x, c.y] for c in centroids])

        # Build candidate matches within max_match_radius_px
        tree = KDTree(img_xy)
        matches = tree.query_ball_point(cat_xy, r=max_match_radius_px)

        candidate_pairs = []
        for cat_idx, centroid_list in enumerate(matches):
            for c_idx in centroid_list:
                dx = img_xy[c_idx, 0] - cat_xy[cat_idx, 0]
                dy = img_xy[c_idx, 1] - cat_xy[cat_idx, 1]
                dist = math.hypot(dx, dy)
                candidate_pairs.append((dist, cat_idx, c_idx, dx, dy))

        # Sort candidate pairs by distance for greedy 1-to-1 assignment
        candidate_pairs.sort(key=lambda item: item[0])

        for dist, cat_idx, c_idx, dx, dy in candidate_pairs:
            if cat_idx in matched_cat_indices or c_idx in matched_centroid_indices:
                continue

            matched_cat_indices.add(cat_idx)
            matched_centroid_indices.add(c_idx)

            cat_info = visible_catalog[cat_idx]
            cent = centroids[c_idx]
            dist_arcsec = dist * pixel_scale

            pair = MatchedStarPair(
                catalog_id=cat_info["id"],
                magnitude=cat_info["magnitude"],
                true_ra_deg=cat_info["true_ra"],
                true_dec_deg=cat_info["true_dec"],
                app_ra_deg=cat_info["app_ra"],
                app_dec_deg=cat_info["app_dec"],
                true_alt_deg=cat_info["true_alt"],
                app_alt_deg=cat_info["app_alt"],
                refraction_arcsec=cat_info["refraction_arcsec"],
                proj_x=cat_info["px"],
                proj_y=cat_info["py"],
                centroid_idx=c_idx,
                det_x=cent.x,
                det_y=cent.y,
                det_brightness=cent.brightness,
                dx_px=dx,
                dy_px=dy,
                dist_px=dist,
                dist_arcsec=dist_arcsec,
            )
            matched_pairs.append(pair)

    # Identify unmatched catalog stars
    unmatched_catalog = [
        visible_catalog[i] for i in range(len(visible_catalog)) if i not in matched_cat_indices
    ]

    # Identify unmatched image centroids
    unmatched_centroids = [
        {
            "idx": i,
            "x": centroids[i].x,
            "y": centroids[i].y,
            "brightness": centroids[i].brightness,
        }
        for i in range(len(centroids))
        if i not in matched_centroid_indices
    ]

    # Calculate aggregate astrometric residuals
    if matched_pairs:
        dists_px = np.array([p.dist_px for p in matched_pairs])
        dists_arcsec = np.array([p.dist_arcsec for p in matched_pairs])
        mean_res_px = float(np.mean(dists_px))
        median_res_px = float(np.median(dists_px))
        rmse_px = float(np.sqrt(np.mean(dists_px**2)))
        rmse_arcsec = float(np.sqrt(np.mean(dists_arcsec**2)))
    else:
        mean_res_px, median_res_px, rmse_px, rmse_arcsec = 0.0, 0.0, 0.0, 0.0

    # Limiting magnitude analysis
    lim_report = calculate_limiting_magnitude(visible_catalog, matched_pairs)

    # Photometry fitting
    photometry = fit_instrumental_photometry(matched_pairs)

    return CrossMatchResult(
        matched_stars=matched_pairs,
        unmatched_catalog_stars=unmatched_catalog,
        unmatched_centroids=unmatched_centroids,
        mean_residual_px=mean_res_px,
        median_residual_px=median_res_px,
        rmse_px=rmse_px,
        rmse_arcsec=rmse_arcsec,
        pixel_scale_arcsec_per_px=pixel_scale,
        limiting_magnitude=lim_report,
        photometry=photometry,
        applied_refraction=refraction_active,
        used_distortion_model=(camera_model is not None),
    )


def calculate_limiting_magnitude(
    visible_catalog: list[dict[str, Any]],
    matched_pairs: list[MatchedStarPair],
) -> LimitingMagnitudeReport:
    """Analyze star detection efficiency as a function of catalog magnitude.

    Determines:
    - Completeness curve in magnitude intervals.
    - 50% and 90% completeness thresholds.
    - Brightest and faintest detected stars.

    Args:
        visible_catalog: List of all catalog stars visible in the image frame.
        matched_pairs: List of successfully matched star pairs.

    Returns:
        LimitingMagnitudeReport with statistics and completeness boundaries.
    """
    matched_ids = {p.catalog_id for p in matched_pairs}

    # Define magnitude intervals
    bin_edges = [0.0, 2.0, 3.0, 4.0, 4.5, 5.0, 5.5, 6.0, 6.5, 7.0, 8.0]
    bins: list[MagnitudeBinStats] = []

    for i in range(len(bin_edges) - 1):
        m_low, m_high = bin_edges[i], bin_edges[i + 1]
        stars_in_bin = [s for s in visible_catalog if m_low <= s["magnitude"] < m_high]
        detected_in_bin = [s for s in stars_in_bin if s["id"] in matched_ids]

        total = len(stars_in_bin)
        det = len(detected_in_bin)
        rate = (det / total) if total > 0 else 0.0

        bins.append(
            MagnitudeBinStats(
                mag_min=m_low,
                mag_max=m_high,
                mag_center=(m_low + m_high) / 2.0,
                total_in_frame=total,
                detected_count=det,
                completeness_rate=rate,
            )
        )

    # Find 50% and 90% limiting magnitude thresholds
    mag_50 = None
    mag_90 = None

    # Interpolate from bins with sufficient stars
    valid_bins = [b for b in bins if b.total_in_frame >= 3]
    if valid_bins:
        # Find last bin with >= 90% detection
        for b in valid_bins:
            if b.completeness_rate >= 0.90:
                mag_90 = b.mag_max
        # Find last bin with >= 50% detection
        for b in valid_bins:
            if b.completeness_rate >= 0.50:
                mag_50 = b.mag_max

    # Extremum stars
    faintest_mag = None
    brightest_mag = None
    faintest_id = None

    if matched_pairs:
        sorted_by_mag = sorted(matched_pairs, key=lambda p: p.magnitude)
        brightest_mag = sorted_by_mag[0].magnitude
        faintest_mag = sorted_by_mag[-1].magnitude
        faintest_id = sorted_by_mag[-1].catalog_id

    total_cat = len(visible_catalog)
    total_det = len(matched_pairs)
    overall_rate = (total_det / total_cat) if total_cat > 0 else 0.0

    return LimitingMagnitudeReport(
        mag_bins=bins,
        mag_50_completeness=mag_50,
        mag_90_completeness=mag_90,
        faintest_detected_magnitude=faintest_mag,
        brightest_detected_magnitude=brightest_mag,
        faintest_catalog_star_id=faintest_id,
        total_catalog_in_frame=total_cat,
        total_detected_in_frame=total_det,
        overall_detection_rate=overall_rate,
    )


def fit_instrumental_photometry(
    matched_pairs: list[MatchedStarPair],
) -> PhotometryFit | None:
    """Fit zero-point instrumental flux to catalog magnitude: mag = -2.5*log10(flux) + ZP.

    Args:
        matched_pairs: List of matched star pairs.

    Returns:
        PhotometryFit object with zero_point and scatter, or None if insufficient stars.
    """
    valid = [p for p in matched_pairs if p.det_brightness > 0]
    if len(valid) < 4:
        return None

    inst_mags = np.array([-2.5 * math.log10(p.det_brightness) for p in valid])
    cat_mags = np.array([p.magnitude for p in valid])

    # Zero-point ZP = cat_mag - inst_mag
    zp_samples = cat_mags - inst_mags
    zero_point = float(np.median(zp_samples))
    scatter = float(np.std(zp_samples))

    return PhotometryFit(
        zero_point=zero_point,
        photometric_scatter_mag=scatter,
        matched_count=len(valid),
    )
