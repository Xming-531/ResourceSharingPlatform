# Generated manually for early return two-party agreement

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0009_order_buyer_return_ok"),
    ]

    operations = [
        migrations.AddField(
            model_name="order",
            name="early_return_buyer_agreed",
            field=models.BooleanField(default=False, verbose_name="买家已确认提前归还"),
        ),
        migrations.AddField(
            model_name="order",
            name="early_return_owner_agreed",
            field=models.BooleanField(default=False, verbose_name="卖家已确认提前归还"),
        ),
    ]
