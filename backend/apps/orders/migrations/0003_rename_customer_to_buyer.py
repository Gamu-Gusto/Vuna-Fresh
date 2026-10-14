from django.db import migrations


class Migration(migrations.Migration):
    """Hand-authored — see users/migrations/0004 for why."""

    dependencies = [
        ("orders", "0002_remove_cartitem_unique_cart_product_and_more"),
        ("users", "0004_rename_customerprofile_to_buyerprofile"),
    ]

    operations = [
        migrations.RenameField(
            model_name="cart",
            old_name="customer",
            new_name="buyer",
        ),
        migrations.RenameField(
            model_name="order",
            old_name="customer",
            new_name="buyer",
        ),
    ]
