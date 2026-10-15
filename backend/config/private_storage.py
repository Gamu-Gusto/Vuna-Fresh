"""
Storage for sensitive uploads: proofs of payment and driver verification
documents (IDs, passports, permits, licences, bank and address documents).

These files never get a public link. They live in a private bucket
(STORAGE_PRIVATE_BUCKET_NAME) — or, without one, in PRIVATE_MEDIA_ROOT on the
server's disk, which isn't served — and reach the people allowed to see them
only through API views that check permissions and write an audit log entry
(see serve_private_file).
"""
import os

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.http import FileResponse


class PrivateFileSystemStorage(FileSystemStorage):
    """Local disk under PRIVATE_MEDIA_ROOT, with no URL. Reads the setting on
    every use (not once at start-up), so tests can point it at a temp folder."""

    def __init__(self):
        super().__init__(base_url=None)

    @property
    def base_location(self):
        return settings.PRIVATE_MEDIA_ROOT

    @property
    def location(self):
        return os.path.abspath(self.base_location)

    def url(self, name):
        raise ValueError("Private files have no URL; serve them with serve_private_file().")


def private_storage():
    """Callable for FileField(storage=...): the private bucket, or local disk."""
    bucket = getattr(settings, "PRIVATE_STORAGE_BUCKET_NAME", "")
    if bucket:
        from storages.backends.s3boto3 import S3Boto3Storage

        return S3Boto3Storage(
            bucket_name=bucket,
            custom_domain=None,   # never the public domain
            querystring_auth=True,  # any URL boto builds is signed and short-lived
            querystring_expire=300,
            default_acl=None,
            file_overwrite=False,
        )
    return PrivateFileSystemStorage()


INLINE_TYPES = {"application/pdf", "image/jpeg", "image/png", "image/webp"}


def serve_private_file(field_file, download_name, content_type=None):
    """
    Stream a private file to an already-authorised user. PDFs and images open
    in the browser; nothing is cached by the browser or any proxy.
    """
    response = FileResponse(
        field_file.open("rb"),
        as_attachment=content_type not in INLINE_TYPES,
        filename=download_name,
        content_type=content_type or "application/octet-stream",
    )
    response["Cache-Control"] = "private, no-store"
    response["X-Content-Type-Options"] = "nosniff"
    # A stray HTML/SVG upload can't run scripts in our origin
    response["Content-Security-Policy"] = "sandbox; default-src 'none'; img-src 'self'; style-src 'unsafe-inline'"
    return response
