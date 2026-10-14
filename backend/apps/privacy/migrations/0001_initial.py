import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ConsentRecord",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("consent_type", models.CharField(
                    choices=[
                        ("data_collection", "Data Collection"),
                        ("marketing", "Marketing"),
                        ("cookies", "Cookies"),
                        ("third_party_sharing", "Third-Party Sharing"),
                    ],
                    max_length=20,
                )),
                ("granted", models.BooleanField(default=False)),
                ("granted_at", models.DateTimeField(blank=True, null=True)),
                ("revoked_at", models.DateTimeField(blank=True, null=True)),
                ("user", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="consent_records",
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={"db_table": "consent_records", "ordering": ["consent_type"]},
        ),
        migrations.AddConstraint(
            model_name="consentrecord",
            constraint=models.UniqueConstraint(fields=["user", "consent_type"], name="unique_user_consent_type"),
        ),
        migrations.CreateModel(
            name="DataAccessRequest",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("request_type", models.CharField(
                    choices=[
                        ("access", "Access"),
                        ("deletion", "Deletion"),
                        ("portability", "Portability"),
                    ],
                    max_length=12,
                )),
                ("status", models.CharField(
                    choices=[
                        ("pending", "Pending"),
                        ("completed", "Completed"),
                        ("denied", "Denied"),
                    ],
                    default="pending",
                    max_length=10,
                )),
                ("requested_at", models.DateTimeField(auto_now_add=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("user", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="data_access_requests",
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={"db_table": "data_access_requests", "ordering": ["-requested_at"]},
        ),
        migrations.CreateModel(
            name="DataAccessAuditLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("reason", models.CharField(max_length=255)),
                ("accessed_at", models.DateTimeField(auto_now_add=True)),
                ("user", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="data_access_audit_logs",
                    to=settings.AUTH_USER_MODEL,
                )),
                ("accessed_by", models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="data_accesses_performed",
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={"db_table": "data_access_audit_logs", "ordering": ["-accessed_at"]},
        ),
    ]
