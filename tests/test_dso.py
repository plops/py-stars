"""Unit tests for Deep Sky Object (DSO) catalog and FOV projection."""

from py_stars.dso import (
    FULL_DSO_CATALOG,
    MESSIER_CATALOG,
    find_dso_by_name,
    get_all_dsos,
    project_dsos_to_image,
)


class MockSolveResult:
    """Mock SolveResult for testing DSO projections."""

    def __init__(self, ra_deg: float = 160.0, dec_deg: float = 45.0, fov_deg: float = 65.0):
        self.ra_deg = ra_deg
        self.dec_deg = dec_deg
        self.fov_deg = fov_deg

    def world_to_pixel(self, ra: float, dec: float) -> tuple[float, float]:
        # Simple projection centered at (ra_deg, dec_deg)
        px = (ra - self.ra_deg) * 30.0
        py = (dec - self.dec_deg) * 30.0
        return px, py


class TestDSOCatalog:
    """Test suite for DSO catalog database."""

    def test_messier_catalog_count(self) -> None:
        """Verify that all 110 Messier objects are cataloged."""
        assert len(MESSIER_CATALOG) == 110
        m_ids = {dso.id for dso in MESSIER_CATALOG}
        for i in range(1, 111):
            assert f"M{i}" in m_ids

    def test_full_catalog_includes_messier_and_ngc(self) -> None:
        """Verify that full catalog includes Messier objects plus bright NGC objects."""
        all_dsos = get_all_dsos()
        assert len(all_dsos) >= 120
        assert len(all_dsos) == len(FULL_DSO_CATALOG)

    def test_find_dso_by_id(self) -> None:
        """Test searching by catalog ID."""
        matches = find_dso_by_name("M31")
        assert len(matches) == 1
        assert matches[0].id == "M31"
        assert "Andromeda" in matches[0].name

    def test_find_dso_by_name(self) -> None:
        """Test searching by common name."""
        matches = find_dso_by_name("Orion")
        assert len(matches) >= 1
        ids = [m.id for m in matches]
        assert "M42" in ids

    def test_find_dso_by_constellation(self) -> None:
        """Test searching by constellation."""
        matches = find_dso_by_name("UMa")
        assert len(matches) >= 5  # M81, M82, M97, M101, M108, M109


class TestDSOProjection:
    """Test suite for DSO projection onto the image plane."""

    def test_project_dsos_returns_visible(self) -> None:
        """Verify projecting DSOs inside the simulated image bounds."""
        solve = MockSolveResult(ra_deg=168.0, dec_deg=55.0, fov_deg=65.0)
        projected = project_dsos_to_image(solve, image_width=4032, image_height=3024)

        assert len(projected) > 0
        p_ids = [p.dso.id for p in projected]
        # M97 Owl Nebula and M108 are at ~RA 168, Dec 55
        assert "M97" in p_ids or "M108" in p_ids

        for p in projected:
            assert p.is_visible is True
            assert 0 <= p.image_x <= 4032
            assert 0 <= p.image_y <= 3024
            assert p.major_axis_px > 0

    def test_magnitude_filter(self) -> None:
        """Verify magnitude filter excludes faint DSOs."""
        solve = MockSolveResult(ra_deg=168.0, dec_deg=55.0, fov_deg=65.0)
        bright_only = project_dsos_to_image(
            solve, image_width=4032, image_height=3024, max_magnitude=7.0
        )
        for p in bright_only:
            assert p.dso.magnitude <= 7.0
