from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0016_order_party_hidden_flags"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="identity_verified",
            field=models.BooleanField(default=False, verbose_name="是否已实名认证"),
        ),
    ]
