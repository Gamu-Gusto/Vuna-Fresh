import os
import uuid

from django.core.files.storage import default_storage

ALLOWED_PROOF_TYPES = {"image/jpeg", "image/png", "image/webp", "application/pdf"}
MAX_PROOF_SIZE = 5 * 1024 * 1024


class InvalidProofFileError(Exception):
    pass


def save_proof_file(file):
    """Validates and stores an uploaded proof of payment, returning its storage path."""
    if file.content_type not in ALLOWED_PROOF_TYPES:
        raise InvalidProofFileError("Upload a PDF, JPEG, PNG or WebP file.")
    if file.size > MAX_PROOF_SIZE:
        raise InvalidProofFileError("File must be under 5 MB.")

    ext = os.path.splitext(file.name)[1].lower() or ".pdf"
    return default_storage.save(f"deposit-proofs/{uuid.uuid4()}{ext}", file)
