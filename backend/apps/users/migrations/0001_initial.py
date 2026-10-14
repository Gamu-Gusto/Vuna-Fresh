import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
import apps.users.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.CreateModel(
            name="User",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("password", models.CharField(max_length=128, verbose_name="password")),
                ("last_login", models.DateTimeField(blank=True, null=True, verbose_name="last login")),
                ("is_superuser", models.BooleanField(default=False, verbose_name="superuser status")),
                ("email", models.EmailField(max_length=254, unique=True)),
                ("phone", models.CharField(blank=True, max_length=20)),
                ("first_name", models.CharField(max_length=150)),
                ("last_name", models.CharField(max_length=150)),
                ("role", models.CharField(choices=[("customer", "Customer"), ("farmer", "Farmer"), ("driver", "Driver"), ("admin", "Admin")], default="customer", max_length=10)),
                ("status", models.CharField(choices=[("pending", "Pending"), ("active", "Active"), ("suspended", "Suspended"), ("deactivated", "Deactivated")], default="pending", max_length=12)),
                ("is_staff", models.BooleanField(default=False)),
                ("is_active", models.BooleanField(default=True)),
                ("date_joined", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("groups", models.ManyToManyField(blank=True, related_name="user_set", related_query_name="user", to="auth.group", verbose_name="groups")),
                ("user_permissions", models.ManyToManyField(blank=True, related_name="user_set", related_query_name="user", to="auth.permission", verbose_name="user permissions")),
            ],
            options={"db_table": "users", "ordering": ["-date_joined"]},
            managers=[("objects", apps.users.models.UserManager())],
        ),
        migrations.CreateModel(
            name="Address",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("label", models.CharField(blank=True, help_text="e.g. Home, Work", max_length=50)),
                ("street_address", models.CharField(max_length=255)),
                ("suburb", models.CharField(blank=True, max_length=100)),
                ("city", models.CharField(max_length=100)),
                ("province", models.CharField(max_length=100)),
                ("postal_code", models.CharField(max_length=10)),
                ("country", models.CharField(default="South Africa", max_length=100)),
                ("is_default", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="addresses", to=settings.AUTH_USER_MODEL)),
            ],
            options={"db_table": "addresses", "ordering": ["-is_default", "-created_at"], "verbose_name_plural": "addresses"},
        ),
        migrations.CreateModel(
            name="CustomerProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("preferred_delivery_address", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to="users.address")),
                ("user", models.OneToOneField(limit_choices_to={"role": "customer"}, on_delete=django.db.models.deletion.CASCADE, related_name="customer_profile", to=settings.AUTH_USER_MODEL)),
            ],
            options={"db_table": "customer_profiles"},
        ),
        migrations.CreateModel(
            name="FarmerProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("farm_name", models.CharField(max_length=255)),
                ("farm_description", models.TextField(blank=True)),
                ("farm_location", models.CharField(blank=True, max_length=255)),
                ("is_approved", models.BooleanField(default=False)),
                ("approved_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("user", models.OneToOneField(limit_choices_to={"role": "farmer"}, on_delete=django.db.models.deletion.CASCADE, related_name="farmer_profile", to=settings.AUTH_USER_MODEL)),
            ],
            options={"db_table": "farmer_profiles"},
        ),
        migrations.CreateModel(
            name="DriverProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("vehicle_type", models.CharField(blank=True, max_length=100)),
                ("vehicle_registration", models.CharField(blank=True, max_length=20)),
                ("is_approved", models.BooleanField(default=False)),
                ("approved_at", models.DateTimeField(blank=True, null=True)),
                ("is_available", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("user", models.OneToOneField(limit_choices_to={"role": "driver"}, on_delete=django.db.models.deletion.CASCADE, related_name="driver_profile", to=settings.AUTH_USER_MODEL)),
            ],
            options={"db_table": "driver_profiles"},
        ),
    ]
