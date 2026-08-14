"""Load iPhone HEIC photos and convert to formats suitable for star detection."""

import numpy as np
from PIL import Image
from pillow_heif import register_heif_opener

# Register HEIF format with Pillow (call once at import time)
register_heif_opener()


def load_heic(filepath: str) -> Image.Image:
    """Load a HEIC file and return as RGB PIL Image.

    Args:
        filepath: Path to the HEIC file.

    Returns:
        PIL Image in RGB mode.

    Raises:
        FileNotFoundError: If the file doesn't exist.
    """
    img = Image.open(filepath)
    return img.convert("RGB")


def load_heic_as_gray(filepath: str) -> np.ndarray:
    """Load a HEIC file and return as grayscale numpy array.

    Args:
        filepath: Path to the HEIC file.

    Returns:
        2D numpy array (height, width) with float64 values in [0, 1].
    """
    img = load_heic(filepath)
    gray = img.convert("L")
    return np.array(gray, dtype=np.float64) / 255.0


def load_heic_as_uint8(filepath: str) -> np.ndarray:
    """Load a HEIC file and return as grayscale uint8 numpy array.

    Args:
        filepath: Path to the HEIC file.

    Returns:
        2D numpy array (height, width) with uint8 values in [0, 255].
    """
    img = load_heic(filepath)
    gray = img.convert("L")
    return np.array(gray, dtype=np.uint8)


def get_image_info(filepath: str) -> dict:
    """Extract basic image information from a HEIC file.

    Args:
        filepath: Path to the HEIC file.

    Returns:
        Dict with keys: width, height, mode, format, exif (dict or None).
    """
    img = Image.open(filepath)
    exif_data = None
    if hasattr(img, "_getexif") and img._getexif():
        exif_data = img._getexif()
    # Also try the getexif() method
    elif hasattr(img, "getexif"):
        exif_raw = img.getexif()
        if exif_raw:
            exif_data = dict(exif_raw)

    return {
        "width": img.width,
        "height": img.height,
        "mode": img.mode,
        "format": img.format,
        "exif": exif_data,
    }
