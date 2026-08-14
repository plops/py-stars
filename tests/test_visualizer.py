"""Tests for visualization."""

import os
import tempfile

import numpy as np
import tetra3rs

from py_stars.visualizer import (
    ensure_output_dir,
    plot_detected_stars,
    plot_star_brightnesses,
)


class TestEnsureOutputDir:
    def test_creates_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test_output")
            result = ensure_output_dir(path)
            assert os.path.isdir(result)


class TestPlotDetectedStars:
    def test_creates_output_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            img = np.random.default_rng(42).integers(0, 50, (100, 100), dtype=np.uint8)
            centroids = [tetra3rs.Centroid(10.0, 10.0, brightness=100.0)]
            path = os.path.join(tmpdir, "stars.png")
            plot_detected_stars(img, centroids, path)
            assert os.path.exists(path)
            assert os.path.getsize(path) > 0


class TestPlotStarBrightnesses:
    def test_creates_output_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            centroids = [
                tetra3rs.Centroid(i * 10.0, i * 10.0, brightness=float(i * 50)) for i in range(10)
            ]
            path = os.path.join(tmpdir, "brightness.png")
            plot_star_brightnesses(centroids, path)
            assert os.path.exists(path)

    def test_handles_empty_centroids(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "empty.png")
            plot_star_brightnesses([], path)  # should not crash
