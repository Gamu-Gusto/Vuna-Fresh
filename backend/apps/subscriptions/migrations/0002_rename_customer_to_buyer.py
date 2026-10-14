import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Hand-authored — see users/migrations/0004 for why. The AlterField (state-only,
    no SQL — the FK constraint already tracks the users.0004 table rename) is
    needed because RenameModel's cross-app propagation depends on migration
    ordering that isn't guaranteed relative to subscriptions.0001_initial; being
    explicit here removes the ambiguity rather than relying on it.
    """

    dependencies = [
        ("subscriptions", "0001_initial"),
        ("users", "0004_rename_customerprofile_to_buyerprofile"),
    ]

    operations = [
        migrations.RenameField(
            model_name="subscription",
            old_name="customer",
            new_name="buyer",
        ),
        migrations.AlterField(
            model_name="subscription",
            name="buyer",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="subscriptions",
                to="users.buyerprofile",
            ),
        ),
    ]
