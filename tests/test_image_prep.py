import base64
import io

import pytest
from PIL import Image

from receipt_expense.image_prep import (
    MAX_LONG_EDGE,
    InvalidImageError,
    encode_base64,
    normalize_to_jpeg,
)


def make_png(width: int, height: int) -> bytes:
    buf = io.BytesIO()
    Image.new("RGBA", (width, height), (200, 100, 50, 255)).save(buf, format="PNG")
    return buf.getvalue()


def test_large_image_is_downscaled():
    jpeg = normalize_to_jpeg(make_png(4000, 3000))
    img = Image.open(io.BytesIO(jpeg))
    assert max(img.size) <= MAX_LONG_EDGE
    assert img.format == "JPEG"


def test_small_image_keeps_size_and_converts_to_rgb():
    jpeg = normalize_to_jpeg(make_png(800, 600))
    img = Image.open(io.BytesIO(jpeg))
    assert img.size == (800, 600)
    assert img.mode == "RGB"


def test_garbage_bytes_raise_invalid_image():
    with pytest.raises(InvalidImageError):
        normalize_to_jpeg(b"this is not an image at all")


def test_encode_base64_roundtrip():
    data = b"\xff\xd8\xff\xe0fakejpeg"
    assert base64.standard_b64decode(encode_base64(data)) == data
