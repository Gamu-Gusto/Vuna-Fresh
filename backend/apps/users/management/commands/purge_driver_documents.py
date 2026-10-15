"""
Deletes driver verification documents Vuna Fresh no longer needs (POPIA: keep
personal information only as long as necessary). For drivers who aren't
approved, a driver's documents are deleted when:
  - their application was rejected 30+ days ago, or
  - they withdrew consent to the document check, or
  - their application was never completed and nothing has happened on it for 30 days.
Approved drivers' documents are kept while they drive for Vuna Fresh.

Run daily if possible; the Render build also runs it on every deploy.
    python manage.py purge_driver_documents [--dry-run]
"""
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db.models import Max
from django.utils import timezone

from apps.privacy.models import ConsentRecord, ConsentType
from apps.users.models import DriverDocument, DriverProfile

RETENTION = timedelta(days=30)


def profiles_to_purge(now=None):
    """[(profile, reason)] for every unapproved driver whose documents should go."""
    cutoff = (now or timezone.now()) - RETENTION
    consenting = set(
        ConsentRecord.objects.filter(consent_type=ConsentType.DRIVER_VERIFICATION, granted=True)
        .values_list("user_id", flat=True)
    )
    result = []
    candidates = (
        DriverProfile.objects.filter(is_approved=False, documents__isnull=False)
        .distinct()
        .annotate(last_upload=Max("documents__uploaded_at"))
        .select_related("user")
    )
    for profile in candidates:
        if profile.rejected_at and profile.rejected_at <= cutoff:
            result.append((profile, "rejected over 30 days ago"))
        elif profile.user_id not in consenting:
            result.append((profile, "consent to the document check withdrawn"))
        elif (
            not profile.rejected_at
            and not profile.verification_status()["complete"]
            and max(profile.last_upload, profile.user.date_joined) <= cutoff
        ):
            result.append((profile, "incomplete application with no activity for 30 days"))
    return result


class Command(BaseCommand):
    help = "Delete documents of rejected, withdrawn or abandoned driver applications (30-day retention)."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="List what would be deleted without deleting.")

    def handle(self, *args, dry_run=False, **options):
        purged = 0
        for profile, reason in profiles_to_purge():
            count = profile.documents.count()
            self.stdout.write(f"Driver #{profile.id}: {count} document(s), {reason}")
            if not dry_run:
                # Deleting each row deletes its private file too (post_delete signal)
                for doc in DriverDocument.objects.filter(driver=profile):
                    doc.delete()
            purged += count
        verb = "Would delete" if dry_run else "Deleted"
        self.stdout.write(self.style.SUCCESS(f"{verb} {purged} driver document(s)."))
