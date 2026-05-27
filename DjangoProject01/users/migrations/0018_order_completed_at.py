from django.db import migrations, models
from django.db.models import F


def backfill_order_completed_at(apps, schema_editor):
    Order = apps.get_model("users", "Order")
    Order.objects.filter(status="已完成", completed_at__isnull=True).update(
        completed_at=F("created_at")
    )


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0017_user_identity_verified"),
    ]

    operations = [
        migrations.AddField(
            model_name="order",
            name="completed_at",
            field=models.DateTimeField(
                blank=True,
                help_text="订单进入「已完成」时写入，用于统计报表",
                null=True,
                verbose_name="成交完成时间",
            ),
        ),
        migrations.RunPython(backfill_order_completed_at, migrations.RunPython.noop),
    ]
