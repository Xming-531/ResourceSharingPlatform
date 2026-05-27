from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0013_billingmessage"),
    ]

    operations = [
        migrations.AddField(
            model_name="order",
            name="normal_return_buyer_requested",
            field=models.BooleanField(
                default=False,
                verbose_name="租借方已发起按时归还（待出租方确认后直接完成）",
            ),
        ),
    ]
