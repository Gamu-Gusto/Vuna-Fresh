import os
import uuid

from django.core.files.storage import default_storage

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_IMAGE_SIZE = 5 * 1024 * 1024


class InvalidImageError(Exception):
    pass


def validate_product_image(file):
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise InvalidImageError("Only JPEG, PNG, WebP, and GIF images are allowed.")
    if file.size > MAX_IMAGE_SIZE:
        raise InvalidImageError("Image must be under 5 MB.")


def store_product_image(file):
    ext = os.path.splitext(file.name)[1].lower() or ".jpg"
    filename = f"products/{uuid.uuid4()}{ext}"
    return default_storage.save(filename, file)


def save_product_image(file):
    """Validates and stores an uploaded product image, returning its storage path.
    Shared by the DRF upload_image endpoint and the Django admin upload widget."""
    validate_product_image(file)
    return store_product_image(file)
