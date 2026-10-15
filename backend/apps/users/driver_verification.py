"""
What a driver must provide before they can be approved, and the checks on it.

Every driver: 21 or older; vehicle registration (RC1), roadworthy certificate,
vehicle licence disc, proof of address from the last 3 months, proof of bank
account. Then, by nationality:
  - South African citizens: SA driver's licence and SA ID book/card.
  - Foreign nationals: their national or international driving licence, a
    passport, and a work permit or asylum document.
The documents themselves are checked by an admin; this module only decides
which ones are needed and whether they're all in.
"""
from datetime import date

from django.db import models

MINIMUM_DRIVER_AGE = 21


class Nationality(models.TextChoices):
    SA_CITIZEN = "sa_citizen", "South African citizen"
    FOREIGN_NATIONAL = "foreign_national", "Foreign national"


class DocumentType(models.TextChoices):
    SA_DRIVERS_LICENCE = "sa_drivers_licence", "South African driver's licence"
    SA_ID = "sa_id", "South African ID book or card"
    FOREIGN_DRIVERS_LICENCE = "foreign_drivers_licence", "National or international driving licence"
    PASSPORT = "passport", "Passport"
    WORK_PERMIT = "work_permit", "Work permit or asylum document"
    VEHICLE_REGISTRATION = "vehicle_registration", "Vehicle registration certificate (RC1)"
    ROADWORTHY_CERTIFICATE = "roadworthy_certificate", "Roadworthy certificate"
    LICENCE_DISC = "licence_disc", "Vehicle licence disc"
    PROOF_OF_ADDRESS = "proof_of_address", "Proof of address"
    PROOF_OF_BANK_ACCOUNT = "proof_of_bank_account", "Proof of bank account"


# Shown to the driver under each item so they upload the right thing
DOCUMENT_HINTS = {
    DocumentType.SA_DRIVERS_LICENCE: "Front and back of your valid licence card.",
    DocumentType.SA_ID: "Your green ID book (photo page) or both sides of your smart ID card.",
    DocumentType.FOREIGN_DRIVERS_LICENCE: "Your valid national licence, or an international driving permit.",
    DocumentType.PASSPORT: "The photo page of your valid passport.",
    DocumentType.WORK_PERMIT: "Your valid work permit, or your asylum seeker or refugee document.",
    DocumentType.VEHICLE_REGISTRATION: "The RC1 registration certificate for the vehicle you'll deliver with.",
    DocumentType.ROADWORTHY_CERTIFICATE: "A valid roadworthy certificate for the same vehicle.",
    DocumentType.LICENCE_DISC: "A clear photo of the current licence disc on the windscreen.",
    DocumentType.PROOF_OF_ADDRESS: "A utility bill, bank statement or lease dated in the last 3 months.",
    DocumentType.PROOF_OF_BANK_ACCOUNT: "A bank confirmation letter or statement showing your name and account number.",
}

FOR_EVERY_DRIVER = [
    DocumentType.VEHICLE_REGISTRATION,
    DocumentType.ROADWORTHY_CERTIFICATE,
    DocumentType.LICENCE_DISC,
    DocumentType.PROOF_OF_ADDRESS,
    DocumentType.PROOF_OF_BANK_ACCOUNT,
]
REQUIRED_DOCUMENTS = {
    Nationality.SA_CITIZEN: [DocumentType.SA_DRIVERS_LICENCE, DocumentType.SA_ID, *FOR_EVERY_DRIVER],
    Nationality.FOREIGN_NATIONAL: [
        DocumentType.FOREIGN_DRIVERS_LICENCE, DocumentType.PASSPORT, DocumentType.WORK_PERMIT, *FOR_EVERY_DRIVER,
    ],
}

ALLOWED_DOCUMENT_TYPES = {"application/pdf", "image/jpeg", "image/png", "image/webp"}
MAX_DOCUMENT_SIZE = 10 * 1024 * 1024  # phone photos of documents can be large


def required_documents(nationality):
    return REQUIRED_DOCUMENTS.get(nationality, [])


def age_on(date_of_birth, today=None):
    today = today or date.today()
    return today.year - date_of_birth.year - ((today.month, today.day) < (date_of_birth.month, date_of_birth.day))


def sa_id_date_of_birth(id_number, today=None):
    """
    Checks a 13-digit South African ID number (format and Luhn check digit) and
    returns the date of birth it encodes (YYMMDD). Raises ValueError if invalid.
    """
    if not (len(id_number) == 13 and id_number.isdigit()):
        raise ValueError("A South African ID number has 13 digits.")

    total = 0
    for i, ch in enumerate(reversed(id_number)):
        digit = int(ch)
        if i % 2 == 1:
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit
    if total % 10 != 0:
        raise ValueError("This ID number isn't valid. Check for a mistyped digit.")

    yy, mm, dd = int(id_number[0:2]), int(id_number[2:4]), int(id_number[4:6])
    today = today or date.today()
    # Two-digit year: the most recent century that doesn't put the birthday in the future
    century = 2000 if 2000 + yy <= today.year else 1900
    try:
        return date(century + yy, mm, dd)
    except ValueError:
        raise ValueError("This ID number doesn't contain a valid date of birth.")
