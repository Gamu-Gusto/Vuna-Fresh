ALLOWED_PROOF_TYPES = {"image/jpeg", "image/png", "image/webp", "application/pdf"}
MAX_PROOF_SIZE = 5 * 1024 * 1024


class InvalidProofFileError(Exception):
    pass


def validate_proof_file(file):
    """Checks an uploaded proof of payment before it's stored (privately, see DirectDepositProof.file)."""
    if file.content_type not in ALLOWED_PROOF_TYPES:
        raise InvalidProofFileError("Upload a PDF, JPEG, PNG or WebP file.")
    if file.size > MAX_PROOF_SIZE:
        raise InvalidProofFileError("File must be under 5 MB.")
