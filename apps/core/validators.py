"""
apps/core/validators.py — reusable file upload validators.
Server-side; never trust file extension alone.
"""

from PIL import Image

from django.core.exceptions import ValidationError
from django.utils.deconstruct import deconstructible


@deconstructible
class FileSizeValidator:
    """Rejects uploads exceeding max_mb megabytes."""

    def __init__(self, max_mb: int = 5):
        self.max_mb = max_mb

    def __call__(self, value):
        limit = self.max_mb * 1024 * 1024
        if value.size > limit:
            raise ValidationError(
                f"File too large. Maximum allowed size is {self.max_mb} MB. "
                f"Your file is {value.size / (1024*1024):.1f} MB."
            )


@deconstructible
class ImageTypeValidator:
    """Rejects uploads that are not valid image files (checks bytes, not extension)."""

    ALLOWED_TYPES = ("JPEG", "PNG", "WEBP", "GIF")

    def __call__(self, value):
        value.seek(0)
        try:
            with Image.open(value) as img:
                img_format = (img.format or "").upper()
                if img_format not in self.ALLOWED_TYPES:
                    raise ValidationError(
                        f"Unsupported image type '{img_format}'. "
                        f"Please upload a JPG, PNG, WebP, or GIF file."
                    )
        except Exception as e:
            if isinstance(e, ValidationError):
                raise
            raise ValidationError("Invalid or corrupted image file.")
        finally:
            value.seek(0)


validate_image_size = FileSizeValidator(max_mb=10)
validate_image_type = ImageTypeValidator()
validate_video_size = FileSizeValidator(max_mb=50)
