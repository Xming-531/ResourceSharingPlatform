from django.db import migrations, models


def seed_home_marquee(apps, schema_editor):
    M = apps.get_model("users", "HomeMarqueeSlide")
    if M.objects.exists():
        return
    rows = [
        # track, sort_order, title, subtitle, image_url
        (1, 10, "光影人像", "摄影灵感 · 示例", "https://picsum.photos/seed/mq1/400/225"),
        (1, 20, "城市街拍", "记录日常", "https://picsum.photos/seed/mq2/400/225"),
        (1, 30, "自然风光", "旅拍主题", "https://picsum.photos/seed/mq3/400/225"),
        (1, 40, "静物小品", "练习构图", "https://picsum.photos/seed/mq4/400/225"),
        (2, 10, "器材租赁", "本平台支持相机镜头出租", "https://picsum.photos/seed/mq5/400/225"),
        (2, 20, "二手出售", "闲置设备上架", "https://picsum.photos/seed/mq6/400/225"),
        (2, 30, "实名交易", "安全下单", "https://picsum.photos/seed/mq7/400/225"),
        (2, 40, "作品广场", "分享你的照片", "https://picsum.photos/seed/mq8/400/225"),
    ]
    for track, so, title, subtitle, url in rows:
        M.objects.create(
            track=track,
            sort_order=so,
            title=title,
            subtitle=subtitle,
            image_url=url,
            enabled=True,
        )


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0019_remove_integerfield_max_length"),
    ]

    operations = [
        migrations.CreateModel(
            name="HomeMarqueeSlide",
            fields=[
                (
                    "slide_id",
                    models.AutoField(
                        primary_key=True, serialize=False, verbose_name="条目ID"
                    ),
                ),
                (
                    "image_url",
                    models.CharField(
                        help_text="可填完整 URL，或以 / 开头的站内路径（如 /images/xxx.jpg）",
                        max_length=512,
                        verbose_name="图片地址",
                    ),
                ),
                ("title", models.CharField(max_length=120, verbose_name="主标题")),
                (
                    "subtitle",
                    models.CharField(
                        blank=True, default="", max_length=200, verbose_name="副标题/说明"
                    ),
                ),
                (
                    "track",
                    models.PositiveSmallIntegerField(
                        choices=[(1, "快轨（上行）"), (2, "慢轨（下行）")],
                        default=1,
                        verbose_name="轨道",
                    ),
                ),
                (
                    "sort_order",
                    models.PositiveIntegerField(
                        default=0,
                        help_text="同轨道内数字越小越靠前",
                        verbose_name="排序",
                    ),
                ),
                ("enabled", models.BooleanField(default=True, verbose_name="启用")),
            ],
            options={
                "verbose_name": "首页跑马灯条目",
                "verbose_name_plural": "首页跑马灯条目",
                "ordering": ["track", "sort_order", "slide_id"],
            },
        ),
        migrations.RunPython(seed_home_marquee, migrations.RunPython.noop),
    ]
