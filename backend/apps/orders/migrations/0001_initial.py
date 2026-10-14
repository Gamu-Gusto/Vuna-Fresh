import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("users", "0001_initial"),
        ("products", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Cart",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("status", models.CharField(
                    choices=[("active", "Active"), ("saved", "Saved"), ("expired", "Expired"), ("converted", "Converted")],
                    default="active",
                    max_length=10,
                )),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("customer", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="carts",
                    to="users.customerprofile",
                )),
            ],
            options={"db_table": "carts", "ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="CartItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("quantity", models.PositiveIntegerField(default=1)),
                ("price_at_add", models.DecimalField(decimal_places=2, max_digits=10)),
                ("cart", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="items",
                    to="orders.cart",
                )),
                ("product", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="+",
                    to="products.product",
                )),
            ],
            options={"db_table": "cart_items"},
        ),
        migrations.AddConstraint(
            model_name="cartitem",
            constraint=models.UniqueConstraint(fields=["cart", "product"], name="unique_cart_product"),
        ),
        migrations.CreateModel(
            name="Order",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("status", models.CharField(
                    choices=[
                        ("placed", "Placed"),
                        ("preparing", "Preparing"),
                        ("ready_for_pickup", "Ready for Pickup"),
                        ("out_for_delivery", "Out for Delivery"),
                        ("delivered", "Delivered"),
                        ("cancelled", "Cancelled"),
                    ],
                    default="placed",
                    max_length=20,
                )),
                ("scheduled_delivery_time", models.DateTimeField(blank=True, null=True)),
                ("subtotal", models.DecimalField(decimal_places=2, max_digits=10)),
                ("delivery_fee", models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ("total", models.DecimalField(decimal_places=2, max_digits=10)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("customer", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="orders",
                    to="users.customerprofile",
                )),
                ("delivery_address", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="orders",
                    to="users.address",
                )),
                ("driver", models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="orders",
                    to="users.driverprofile",
                )),
            ],
            options={"db_table": "orders", "ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="OrderItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("quantity", models.PositiveIntegerField()),
                ("price_at_purchase", models.DecimalField(decimal_places=2, max_digits=10)),
                ("order", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="items",
                    to="orders.order",
                )),
                ("product", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="+",
                    to="products.product",
                )),
                ("farmer", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="order_items",
                    to="users.farmerprofile",
                )),
            ],
            options={"db_table": "order_items"},
        ),
        migrations.CreateModel(
            name="OrderStatusHistory",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("status", models.CharField(
                    choices=[
                        ("placed", "Placed"),
                        ("preparing", "Preparing"),
                        ("ready_for_pickup", "Ready for Pickup"),
                        ("out_for_delivery", "Out for Delivery"),
                        ("delivered", "Delivered"),
                        ("cancelled", "Cancelled"),
                    ],
                    max_length=20,
                )),
                ("changed_at", models.DateTimeField(auto_now_add=True)),
                ("order", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="status_history",
                    to="orders.order",
                )),
                ("changed_by", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="order_status_changes",
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={"db_table": "order_status_history", "ordering": ["changed_at"]},
        ),
    ]
