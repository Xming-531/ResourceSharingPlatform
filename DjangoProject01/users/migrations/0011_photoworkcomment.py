# Generated manually

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0010_order_early_return_flags"),
    ]

    operations = [
        migrations.CreateModel(
            name="PhotoWorkComment",
            fields=[
                (
                    "comment_id",
                    models.AutoField(
                        primary_key=True, serialize=False, verbose_name="评论ID"
                    ),
                ),
                ("user_id", models.IntegerField(verbose_name="评论用户ID")),
                ("content", models.TextField(max_length=2000, verbose_name="内容")),
                (
                    "status",
                    models.CharField(
                        choices=[("待审核", "待审核"), ("已通过", "已通过"), ("已驳回", "已驳回")],
                        default="待审核",
                        max_length=20,
                        verbose_name="审核状态",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="创建时间"),
                ),
                (
                    "photo_work",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="comments",
                        to="users.photowork",
                        verbose_name="作品",
                    ),
                ),
            ],
            options={
                "verbose_name": "作品评论",
                "verbose_name_plural": "作品评论",
                "ordering": ["-created_at"],
            },
        ),
    ]
