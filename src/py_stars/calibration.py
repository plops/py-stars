"""Camera distortion modeling and multi-frame calibration for tetra3rs."""

import os
from typing import Any

import tetra3rs

# Path to built-in / cached camera calibration models
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
DEFAULT_RADIAL_MODEL_PATH = os.path.join(DATA_DIR, "iphone11_camera_radial.bin")
DEFAULT_POLY_MODEL_PATH = os.path.join(DATA_DIR, "iphone11_camera_poly.bin")


def load_camera_model(path: str) -> tetra3rs.CameraModel:
    """Load a CameraModel from a binary file.

    Args:
        path: Path to the camera model .bin file.

    Returns:
        Loaded tetra3rs.CameraModel object.

    Raises:
        FileNotFoundError: If the model file is not found.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"Camera model file not found: {path}")
    return tetra3rs.CameraModel.load_from_file(path)


def save_camera_model(model: tetra3rs.CameraModel, path: str) -> None:
    """Save a CameraModel to a binary file.

    Args:
        model: tetra3rs.CameraModel object.
        path: Destination file path.
    """
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    model.save_to_file(path)


def get_default_camera_model(
    model_type: str = "radial",
    data_dir: str = DATA_DIR,
) -> tetra3rs.CameraModel | None:
    """Retrieve the default pre-calibrated CameraModel if available.

    Args:
        model_type: "radial" or "polynomial".
        data_dir: Directory where calibration models are stored.

    Returns:
        CameraModel or None if no pre-calibrated model exists.
    """
    if model_type == "radial":
        target = os.path.join(data_dir, "iphone11_camera_radial.bin")
    else:
        target = os.path.join(data_dir, "iphone11_camera_poly.bin")

    if os.path.exists(target):
        try:
            return load_camera_model(target)
        except Exception:
            return None
    return None


def calibrate_camera_from_solves(
    db: tetra3rs.SolverDatabase,
    solve_results: list[Any],
    centroids_list: list[list[Any]],
    image_width: int,
    image_height: int,
    model: str = "radial",
    order: int = 3,
) -> tetra3rs.CalibrateResult:
    """Calibrate camera distortion across multiple plate-solved frames.

    Args:
        db: tetra3rs.SolverDatabase instance.
        solve_results: List of successful SolveResult objects.
        centroids_list: List of centroid lists corresponding to each solve result.
        image_width: Image width in pixels.
        image_height: Image height in pixels.
        model: Distortion model type: "radial" (Brown-Conrady) or "polynomial".
        order: Polynomial order (used when model="polynomial", default 3).

    Returns:
        tetra3rs.CalibrateResult containing the fitted .camera_model and stats.
    """
    if not solve_results or len(solve_results) != len(centroids_list):
        raise ValueError(
            "solve_results and centroids_list must be non-empty and have matching length."
        )

    if model == "polynomial":
        return db.calibrate_camera(
            solve_results,
            centroids_list,
            image_width=image_width,
            image_height=image_height,
            model="polynomial",
            order=order,
        )
    else:
        return db.calibrate_camera(
            solve_results,
            centroids_list,
            image_width=image_width,
            image_height=image_height,
            model="radial",
        )
