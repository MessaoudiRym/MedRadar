"""Check and prepare a medicine box photo, in memory only.

The photo is never written to disk, to the database or to the logs.
"""

from io import BytesIO

from PIL import Image, ImageOps, UnidentifiedImageError

MAX_BYTES = 5 * 1024 * 1024  # 5 MB
MAX_SIDE = 1600              # pixels, longest side, after preparation
MAX_PIXELS = 50_000_000      # refuse "decompression bombs" before decoding them
JPEG_QUALITY = 85

# The real type is read from the first bytes, never from the name or the declared type
SIGNATURES = {
    "JPEG": lambda b: b.startswith(b"\xff\xd8\xff"),
    "PNG": lambda b: b.startswith(b"\x89PNG\r\n\x1a\n"),
    "WEBP": lambda b: b[:4] == b"RIFF" and b[8:12] == b"WEBP",
}

NOT_AN_IMAGE = "Format non accepté. Envoyez une photo JPEG, PNG ou WebP."
TOO_LARGE = "Photo trop lourde (5 Mo maximum). Prenez une photo plus légère ou tapez le nom."


class ImageRejected(Exception):
    def __init__(self, status: int, code: str, message: str):
        super().__init__(message)
        self.status, self.code, self.message = status, code, message


def detect_type(data: bytes) -> str | None:
    return next((kind for kind, matches in SIGNATURES.items() if matches(data)), None)


def prepare_image(data: bytes) -> bytes:
    """JPEG, upright (EXIF orientation applied), at most 1600 px, without metadata.

    Metadata (EXIF) is dropped: a phone photo can contain the GPS position.
    """
    if len(data) > MAX_BYTES:
        raise ImageRejected(413, "trop_lourde", TOO_LARGE)
    kind = detect_type(data)
    if kind is None:
        raise ImageRejected(415, "format", NOT_AN_IMAGE)

    try:
        with Image.open(BytesIO(data)) as image:
            if image.format != kind:
                raise ImageRejected(415, "format", NOT_AN_IMAGE)
            width, height = image.size
            if width * height > MAX_PIXELS:
                raise ImageRejected(413, "trop_lourde", TOO_LARGE)
            image = ImageOps.exif_transpose(image)
            image.thumbnail((MAX_SIDE, MAX_SIDE))
            if image.mode != "RGB":
                # Transparent parts become white, not black
                background = Image.new("RGB", image.size, "white")
                rgba = image.convert("RGBA")
                background.paste(rgba, mask=rgba.getchannel("A"))
                image = background
            out = BytesIO()
            image.save(out, "JPEG", quality=JPEG_QUALITY)
            return out.getvalue()
    except ImageRejected:
        raise
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
        # Truncated or damaged file
        raise ImageRejected(415, "format", NOT_AN_IMAGE) from None
