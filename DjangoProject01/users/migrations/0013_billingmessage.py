from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0012_photowork_status_rejected"),
    ]

    operations = [
        migrations.CreateModel(
            name="BillingMessage",
            fields=[
                (
                    "message_id",
                    models.AutoField(
                        primary_key=True, serialize=False, verbose_name="消息ID"
                    ),
                ),
                ("user_id", models.IntegerField(verbose_name="接收用户ID")),
                (
                    "order_id",
                    models.IntegerField(blank=True, null=True, verbose_name="关联订单ID"),
                ),
                (
                    "key",
                    models.CharField(max_length=96, unique=True, verbose_name="幂等键"),
                ),
                ("kind", models.CharField(max_length=16, verbose_name="类型")),
                (
                    "amount",
                    models.DecimalField(
                        decimal_places=2, max_digits=12, verbose_name="金额"
                    ),
                ),
                ("remark", models.TextField(verbose_name="备注")),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="创建时间"),
                ),
            ],
            options={
                "verbose_name": "账单消息",
                "verbose_name_plural": "账单消息",
                "ordering": ["-created_at"],
            },
        ),
    ]
