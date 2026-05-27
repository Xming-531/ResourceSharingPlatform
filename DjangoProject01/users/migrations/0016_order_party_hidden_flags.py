from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0015_merge_order_line_rental_schedule"),
    ]

    operations = [
        migrations.AddField(
            model_name="order",
            name="hidden_from_buyer",
            field=models.BooleanField(default=False, verbose_name="买方/租借方已从列表移除（软删）"),
        ),
        migrations.AddField(
            model_name="order",
            name="hidden_from_owner",
            field=models.BooleanField(default=False, verbose_name="卖方/出租方已从列表移除（软删）"),
        ),
    ]
