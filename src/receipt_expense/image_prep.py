"""Prepare receipt photos for the vision API: rotate, downscale, re-encode, base64."""

import base64
import io
import logging

from PIL import Image, ImageOps, UnidentifiedImageError

logger = logging.getLogger(__name__)

MAX_LONG_EDGE = 2000
JPEG_QUALITY = 85
MEDIA_TYPE = "image/jpeg"


class InvalidImageError(ValueError):
    """The uploaded bytes are not a readable image."""


def normalize_to_jpeg(raw: bytes) -> bytes:
    """Normalize an uploaded photo into clean JPEG bytes.

    - applies EXIF orientation (phone photos are often stored rotated)
    - downscales so the long edge is at most MAX_LONG_EDGE px
    - re-encodes as JPEG to keep the API request small
    """
    try:
        image = Image.open(io.BytesIO(raw))
        image.load()
    except (UnidentifiedImageError, OSError) as exc:
        raise InvalidImageError("Uploaded file is not a readable image") from exc

    image = ImageOps.exif_transpose(image)

    if max(image.size) > MAX_LONG_EDGE:
        image.thumbnail((MAX_LONG_EDGE, MAX_LONG_EDGE), Image.LANCZOS)

    if image.mode != "RGB":
        image = image.convert("RGB")

    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=JPEG_QUALITY)
    jpeg_bytes = buffer.getvalue()
    logger.info(
        "Prepared image: %dx%d, %d KB", image.width, image.height, len(jpeg_bytes) // 1024
    )
    return jpeg_bytes


def encode_base64(jpeg_bytes: bytes) -> str:
    """Base64-encode normalized JPEG bytes for the vision API."""
    return base64.standard_b64encode(jpeg_bytes).decode("ascii")
