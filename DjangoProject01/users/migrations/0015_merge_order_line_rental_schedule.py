import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0014_order_normal_return_buyer_requested"),
    ]

    operations = [
        migrations.AddField(
            model_name="order",
            name="deposit_amount",
            field=models.DecimalField(
                decimal_places=2, default=0, max_digits=10, verbose_name="押金金额"
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="order",
            name="equipment_id",
            field=models.IntegerField(default=0, verbose_name="设备ID"),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="order",
            name="rental_days",
            field=models.IntegerField(default=1, verbose_name="租借天数"),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="order",
            name="rental_price",
            field=models.DecimalField(
                decimal_places=2, default=0, max_digits=10, verbose_name="日租金/单价"
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="order",
            name="subtotal",
            field=models.DecimalField(
                decimal_places=2, default=0, max_digits=10, verbose_name="租金/售价小计"
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="rentalschedule",
            name="order",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="rental_schedule",
                to="users.order",
                verbose_name="订单",
            ),
        ),
        migrations.RemoveField(
            model_name="rentalschedule",
            name="order_item",
        ),
        migrations.AlterField(
            model_name="rentalschedule",
            name="order",
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="rental_schedule",
                to="users.order",
                verbose_name="订单",
            ),
        ),
        migrations.DeleteModel(
            name="OrderItem",
        ),
    ]
