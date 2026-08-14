"""py-stars: Detect stars in iPhone HEIC photos using tetra3rs for plate solving."""

__version__ = "0.1.0"

from py_stars.heic_loader import (
    get_image_info,
    load_heic,
    load_heic_as_gray,
    load_heic_as_uint8,
)

__all__ = [
    "get_image_info",
    "load_heic",
    "load_heic_as_gray",
    "load_heic_as_uint8",
]
