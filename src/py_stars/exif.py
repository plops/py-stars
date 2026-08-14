"""EXIF metadata extraction and camera optical parameter estimation."""

import math
from datetime import datetime, timezone
from typing import Any

from PIL import ExifTags, Image
from pillow_heif import register_heif_opener

# Ensure HEIF opener is registered
register_heif_opener()


def parse_exif(filepath_or_image: str | Image.Image) -> dict[str, Any]:
    """Extract and decode all EXIF metadata from an image.

    Args:
        filepath_or_image: Path to image file or PIL Image object.

    Returns:
        Dictionary of decoded EXIF tags and IFD sub-dictionaries.
    """
    if isinstance(filepath_or_image, str):
        img = Image.open(filepath_or_image)
    else:
        img = filepath_or_image

    exif = img.getexif()
    if not exif:
        return {}

    exif_data: dict[str, Any] = {}

    # Root tags
    for tag_id, value in exif.items():
        tag_name = ExifTags.TAGS.get(tag_id, str(tag_id))
        exif_data[tag_name] = value

    # IFDs (Exif, GPSInfo, MakerNote, etc.)
    for ifd_id in ExifTags.IFD:
        try:
            ifd = exif.get_ifd(ifd_id)
            if ifd:
                if ifd_id.name == "GPSInfo":
                    gps_dict = {ExifTags.GPSTAGS.get(k, str(k)): v for k, v in ifd.items()}
                    exif_data["GPSInfo"] = gps_dict
                else:
                    sub_dict = {ExifTags.TAGS.get(k, str(k)): v for k, v in ifd.items()}
                    exif_data[ifd_id.name] = sub_dict
        except Exception:
            pass

    return exif_data


def compute_camera_fov(
    exif_data_or_filepath: dict[str, Any] | str | Image.Image,
    image_width: int | None = None,
    image_height: int | None = None,
    fallback_hfov: float = 67.3,
) -> tuple[float, float, float]:
    """Compute camera horizontal, vertical, and diagonal field of view (FOV) from EXIF.

    Uses 35mm equivalent focal length (FocalLengthIn35mmFilm) or physical focal length
    combined with the image aspect ratio. Does not require hardcoded device constants.

    Args:
        exif_data_or_filepath: EXIF dict, file path, or PIL Image.
        image_width: Optional image width in pixels.
        image_height: Optional image height in pixels.
        fallback_hfov: Fallback HFOV in degrees if focal length is not found in EXIF.

    Returns:
        Tuple of (hfov_deg, vfov_deg, dfov_deg).
    """
    if isinstance(exif_data_or_filepath, (str, Image.Image)):
        exif_data = parse_exif(exif_data_or_filepath)
        if isinstance(exif_data_or_filepath, str):
            with Image.open(exif_data_or_filepath) as im:
                image_width = image_width or im.width
                image_height = image_height or im.height
        elif isinstance(exif_data_or_filepath, Image.Image):
            image_width = image_width or exif_data_or_filepath.width
            image_height = image_height or exif_data_or_filepath.height
    else:
        exif_data = exif_data_or_filepath

    w = float(image_width or 4032)
    h = float(image_height or 3024)
    aspect = w / h if h > 0 else 4.0 / 3.0

    # Extract 35mm equivalent focal length
    focal_35 = None
    if "Exif" in exif_data and isinstance(exif_data["Exif"], dict):
        focal_35 = exif_data["Exif"].get("FocalLengthIn35mmFilm")
    if focal_35 is None:
        focal_35 = exif_data.get("FocalLengthIn35mmFilm")

    if focal_35 and float(focal_35) > 0:
        f_mm = float(focal_35)
        # Standard 35mm full frame diagonal is sqrt(36^2 + 24^2) = 43.2666 mm
        # For a sensor with aspect ratio `aspect`, the equivalent sensor dimensions are:
        # w_eq^2 + h_eq^2 = diag^2  =>  w_eq = diag / sqrt(1 + 1/aspect^2)
        diag_35 = math.hypot(36.0, 24.0)  # 43.266615 mm
        w_eq = diag_35 / math.sqrt(1.0 + 1.0 / (aspect * aspect))
        h_eq = w_eq / aspect

        hfov = 2.0 * math.degrees(math.atan(w_eq / (2.0 * f_mm)))
        vfov = 2.0 * math.degrees(math.atan(h_eq / (2.0 * f_mm)))
        dfov = 2.0 * math.degrees(math.atan(diag_35 / (2.0 * f_mm)))
        return hfov, vfov, dfov

    # Check physical focal length
    focal_phys = None
    if "Exif" in exif_data and isinstance(exif_data["Exif"], dict):
        focal_phys = exif_data["Exif"].get("FocalLength")
    if focal_phys is None:
        focal_phys = exif_data.get("FocalLength")

    if focal_phys and float(focal_phys) > 0:
        # If we have focal length but not 35mm equiv, estimate from fallback HFOV
        pass

    vfov_fallback = 2.0 * math.degrees(
        math.atan(math.tan(math.radians(fallback_hfov / 2.0)) / aspect)
    )
    dfov_fallback = 2.0 * math.degrees(
        math.atan(
            math.hypot(
                math.tan(math.radians(fallback_hfov / 2.0)),
                math.tan(math.radians(vfov_fallback / 2.0)),
            )
        )
    )
    return fallback_hfov, vfov_fallback, dfov_fallback


def get_gps_info(exif_data_or_filepath: dict[str, Any] | str) -> dict[str, Any] | None:
    """Extract GPS coordinates, altitude, UTC timestamp, and compass heading from EXIF.

    Args:
        exif_data_or_filepath: EXIF dict or file path.

    Returns:
        Dict with keys: latitude_deg, longitude_deg, altitude_m, utc_datetime,
        compass_heading_deg, positioning_error_m; or None if GPS info is missing.
    """
    if isinstance(exif_data_or_filepath, str):
        exif_data = parse_exif(exif_data_or_filepath)
    else:
        exif_data = exif_data_or_filepath

    gps = exif_data.get("GPSInfo")
    if not gps or not isinstance(gps, dict):
        return None

    try:
        # Latitude
        lat_tuple = gps.get("GPSLatitude")
        lat_ref = gps.get("GPSLatitudeRef", "N")
        if lat_tuple is None:
            return None
        lat = float(lat_tuple[0]) + float(lat_tuple[1]) / 60.0 + float(lat_tuple[2]) / 3600.0
        if str(lat_ref).upper() == "S":
            lat = -lat

        # Longitude
        lon_tuple = gps.get("GPSLongitude")
        lon_ref = gps.get("GPSLongitudeRef", "E")
        if lon_tuple is None:
            return None
        lon = float(lon_tuple[0]) + float(lon_tuple[1]) / 60.0 + float(lon_tuple[2]) / 3600.0
        if str(lon_ref).upper() == "W":
            lon = -lon

        # Altitude
        alt = None
        if "GPSAltitude" in gps:
            alt = float(gps["GPSAltitude"])
            alt_ref = gps.get("GPSAltitudeRef", 0)
            if alt_ref == 1 or alt_ref == b"\x01":
                alt = -alt

        # UTC Timestamp from GPS
        utc_dt = None
        date_str = gps.get("GPSDateStamp")
        time_tuple = gps.get("GPSTimeStamp")
        if date_str and time_tuple:
            parts = [int(p) for p in str(date_str).split(":")]
            h = int(time_tuple[0])
            m = int(time_tuple[1])
            s_float = float(time_tuple[2])
            s = int(s_float)
            micro = int((s_float - s) * 1_000_000)
            utc_dt = datetime(parts[0], parts[1], parts[2], h, m, s, micro, tzinfo=timezone.utc)

        # Fallback to EXIF DateTimeOriginal if GPS timestamp is not present
        if utc_dt is None:
            exif_sub = exif_data.get("Exif", {})
            dt_str = exif_sub.get("DateTimeOriginal") or exif_data.get("DateTimeOriginal")
            if dt_str:
                try:
                    dt_clean = str(dt_str).strip()
                    # format: "YYYY:MM:DD HH:MM:SS"
                    d_part, t_part = dt_clean.split(" ")
                    y, mo, d = [int(x) for x in d_part.split(":")]
                    hh, mm, ss = [int(x) for x in t_part.split(":")]
                    utc_dt = datetime(y, mo, d, hh, mm, ss, tzinfo=timezone.utc)
                except Exception:
                    pass

        # Compass heading
        heading = None
        if "GPSImgDirection" in gps:
            heading = float(gps["GPSImgDirection"])
        elif "GPSDestBearing" in gps:
            heading = float(gps["GPSDestBearing"])

        # Positioning error
        pos_error = None
        if "GPSHPositioningError" in gps:
            pos_error = float(gps["GPSHPositioningError"])

        return {
            "latitude_deg": lat,
            "longitude_deg": lon,
            "altitude_m": alt if alt is not None else 0.0,
            "utc_datetime": utc_dt,
            "compass_heading_deg": heading,
            "positioning_error_m": pos_error,
        }
    except Exception:
        return None
