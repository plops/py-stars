"""Tests for star matching, astrometric residuals, and limiting magnitude."""

from py_stars.star_matching import (
    MatchedStarPair,
    calculate_limiting_magnitude,
    fit_instrumental_photometry,
)


class TestLimitingMagnitude:
    """Tests for calculate_limiting_magnitude."""

    def test_completeness_curve(self):
        # Synthetic catalog stars: 10 stars from mag 1.0 to 6.0
        catalog = [
            {"id": 1, "magnitude": 1.5},
            {"id": 2, "magnitude": 2.2},
            {"id": 3, "magnitude": 2.8},
            {"id": 4, "magnitude": 3.5},
            {"id": 5, "magnitude": 3.9},
            {"id": 6, "magnitude": 4.2},
            {"id": 7, "magnitude": 4.8},
            {"id": 8, "magnitude": 5.2},
            {"id": 9, "magnitude": 5.8},
            {"id": 10, "magnitude": 6.5},
        ]

        # Only stars with mag <= 4.0 detected
        matched_pairs = [
            MatchedStarPair(
                catalog_id=s["id"],
                magnitude=s["magnitude"],
                true_ra_deg=0.0,
                true_dec_deg=0.0,
                app_ra_deg=0.0,
                app_dec_deg=0.0,
                true_alt_deg=45.0,
                app_alt_deg=45.0,
                refraction_arcsec=0.0,
                proj_x=0.0,
                proj_y=0.0,
                centroid_idx=i,
                det_x=0.0,
                det_y=0.0,
                det_brightness=100.0,
                dx_px=0.0,
                dy_px=0.0,
                dist_px=0.0,
                dist_arcsec=0.0,
            )
            for i, s in enumerate(catalog)
            if s["magnitude"] <= 4.0
        ]

        report = calculate_limiting_magnitude(catalog, matched_pairs)

        assert report.total_catalog_in_frame == 10
        assert report.total_detected_in_frame == 5
        assert report.brightest_detected_magnitude == 1.5
        assert report.faintest_detected_magnitude == 3.9


class TestPhotometryFit:
    """Tests for instrumental flux fitting."""

    def test_fits_zero_point(self):
        # mag = -2.5*log10(flux) + ZP
        # If ZP = 15.0: flux = 1000 => -2.5*log10(1000) = -7.5 => mag = 7.5
        import math

        pairs = []
        for i in range(5):
            flux = 1000.0 * (i + 1)
            mag = -2.5 * math.log10(flux) + 15.0
            pairs.append(
                MatchedStarPair(
                    catalog_id=i,
                    magnitude=mag,
                    true_ra_deg=0.0,
                    true_dec_deg=0.0,
                    app_ra_deg=0.0,
                    app_dec_deg=0.0,
                    true_alt_deg=45.0,
                    app_alt_deg=45.0,
                    refraction_arcsec=0.0,
                    proj_x=0.0,
                    proj_y=0.0,
                    centroid_idx=i,
                    det_x=0.0,
                    det_y=0.0,
                    det_brightness=flux,
                    dx_px=0.0,
                    dy_px=0.0,
                    dist_px=0.0,
                    dist_arcsec=0.0,
                )
            )

        fit = fit_instrumental_photometry(pairs)
        assert fit is not None
        assert abs(fit.zero_point - 15.0) < 1e-4
        assert fit.photometric_scatter_mag < 1e-4
