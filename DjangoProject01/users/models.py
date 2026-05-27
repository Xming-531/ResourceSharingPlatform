from django.db import models
from django.contrib.auth.models import AbstractUser
import uuid


class User(AbstractUser):
    phone = models.CharField(max_length=20, verbose_name="联系电话")
    identity_verified = models.BooleanField(default=False, verbose_name="是否已实名认证")
    avatar_url = models.CharField(
        max_length=255, null=True, blank=True, verbose_name="头像地址"
    )
    role = models.CharField(max_length=4, verbose_name="用户角色")
    status = models.IntegerField(verbose_name="账户状态")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="账户创建时间")


    groups = models.ManyToManyField(
        "auth.Group",
        verbose_name="groups",
        blank=True,
        related_name="users_user_set",
        related_query_name="users_user",
    )
    user_permissions = models.ManyToManyField(
        "auth.Permission",
        verbose_name="user permissions",
        blank=True,
        related_name="users_user_set",
        related_query_name="users_user",
    )

    class Meta:
        verbose_name = "用户"
        verbose_name_plural = "用户"


class AuthToken(models.Model):
    """
    Very small token table for SPA authentication.

    Frontend sends: Authorization: Bearer <token> (or Token <token>)
    """

    key = models.CharField(max_length=64, primary_key=True)
    user = models.ForeignKey(
        "users.User", on_delete=models.CASCADE, related_name="tokens"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    @staticmethod
    def new_key() -> str:
        return uuid.uuid4().hex


class Equipment(models.Model):
    LISTING_RENT = "rent"
    LISTING_SALE = "sale"
    LISTING_CHOICES = (
        (LISTING_RENT, "出租"),
        (LISTING_SALE, "出售"),
    )

    # 商品状态（公开展示仅 status == STATUS_ON_SHELF）
    STATUS_PENDING_REVIEW = "待审核"
    STATUS_ON_SHELF = "已上架"
    STATUS_REJECTED = "已驳回"
    STATUS_OFF = "已下架"
    STATUS_WITHDRAWN = "已撤回"
    STATUS_SOLD = "已卖出"
    STATUS_RENTING = "租赁中"
    STATUS_PENDING_DELIVERY = "待交付"
    STATUS_PENDING_PICKUP = "待取货"

    equipment_id = models.AutoField(primary_key=True, verbose_name="主键ID")
    owner_id = models.IntegerField(verbose_name="设备拥有者ID")
    title = models.CharField(max_length=255, verbose_name="设备名称")
    category = models.CharField(max_length=50, verbose_name="上架分类")
    brand = models.CharField(max_length=50, verbose_name="设备品牌")
    model = models.CharField(max_length=50, verbose_name="设备型号")
    description = models.TextField(verbose_name="设备描述")
    listing_type = models.CharField(
        max_length=10,
        choices=LISTING_CHOICES,
        default=LISTING_RENT,
        verbose_name="出租/出售",
    )
    price = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name="设备日租金/价格"
    )
    deposit = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="设备押金")
    cover_img_url = models.CharField(
        max_length=255, null=True, blank=True, verbose_name="设备封面图片存储路径"
    )
    status = models.CharField(max_length=20, verbose_name="设备状态")
    location = models.CharField(max_length=255, verbose_name="设备位置")
    view_count = models.IntegerField(verbose_name="设备浏览次数")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="设备创建时间")


class Favorite(models.Model):
    """用户收藏的商品。"""

    favorite_id = models.AutoField(primary_key=True, verbose_name="收藏ID")
    user = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="favorites",
        verbose_name="用户",
    )
    equipment = models.ForeignKey(
        Equipment,
        on_delete=models.CASCADE,
        related_name="favorite_records",
        verbose_name="商品",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="收藏时间")

    class Meta:
        verbose_name = "收藏"
        verbose_name_plural = "收藏"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "equipment"], name="uniq_user_equipment_favorite"
            ),
        ]


class Order(models.Model):
    TYPE_RENT = "rent"
    TYPE_SALE = "sale"
    TYPE_CHOICES = ((TYPE_RENT, "租赁"), (TYPE_SALE, "出售"))

    order_id = models.AutoField(primary_key=True, verbose_name="主键ID")
    user_id = models.IntegerField(verbose_name="用户ID")
    owner_id = models.IntegerField(verbose_name="卖家/出租方用户ID", default=0)
    order_type = models.CharField(
        max_length=10, choices=TYPE_CHOICES, default=TYPE_RENT, verbose_name="订单类型"
    )
    total_amount = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name="订单总金额"
    )
    status = models.CharField(max_length=20, verbose_name="订单状态")
    shipping_address = models.TextField(verbose_name="收货地址")
    contact_phone = models.CharField(max_length=20, verbose_name="联系电话")
    equipment_id = models.IntegerField(verbose_name="设备ID")
    rental_days = models.IntegerField(verbose_name="租借天数", default=1)
    rental_price = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name="日租金/单价"
    )
    subtotal = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name="租金/售价小计"
    )
    deposit_amount = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name="押金金额", default=0
    )
    owner_handover_ok = models.BooleanField(default=False, verbose_name="出租方/卖家已确认交接")
    buyer_handover_ok = models.BooleanField(default=False, verbose_name="买家已确认交接")
    owner_return_ok = models.BooleanField(default=False, verbose_name="出租方确认归还/订单完成")
    buyer_return_ok = models.BooleanField(default=False, verbose_name="承租方确认归还")
    early_return_buyer_agreed = models.BooleanField(
        default=False, verbose_name="买家已确认提前归还"
    )
    early_return_owner_agreed = models.BooleanField(
        default=False, verbose_name="卖家已确认提前归还"
    )
    normal_return_buyer_requested = models.BooleanField(
        default=False,
        verbose_name="租借方已发起按时归还（待出租方确认后直接完成）",
    )
    hidden_from_buyer = models.BooleanField(
        default=False,
        verbose_name="买方/租借方已从列表移除（软删）",
    )
    hidden_from_owner = models.BooleanField(
        default=False,
        verbose_name="卖方/出租方已从列表移除（软删）",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="订单创建时间")
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="成交完成时间",
        help_text="订单进入「已完成」时写入，用于统计报表",
    )


class PhotoWork(models.Model):
    """照片展示：用户发布的摄影作品（管理员审核后公开展示）。"""

    STATUS_PENDING = "待审核"
    STATUS_APPROVED = "已上架"
    STATUS_OFF = "已下架"
    STATUS_REJECTED = "已驳回"
    STATUS_WITHDRAWN = "已撤回"
    STATUS_CHOICES = (
        (STATUS_PENDING, "待审核"),
        (STATUS_APPROVED, "已上架"),
        (STATUS_OFF, "已下架"),
        (STATUS_REJECTED, "已驳回"),
        (STATUS_WITHDRAWN, "已撤回"),
    )

    work_id = models.AutoField(primary_key=True, verbose_name="作品ID")
    user_id = models.IntegerField(verbose_name="发布用户ID")
    image_url = models.CharField(max_length=255, verbose_name="图片地址")

    camera_name = models.CharField(max_length=100, verbose_name="相机名称")
    lens_name = models.CharField(max_length=100, verbose_name="镜头名称")
    iso = models.CharField(max_length=30, verbose_name="感光度")
    shutter_speed = models.CharField(max_length=30, verbose_name="曝光时间")
    aperture = models.CharField(max_length=30, verbose_name="光圈大小")
    shoot_location = models.CharField(max_length=255, verbose_name="拍摄地点")

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        verbose_name="审核状态",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")


class PhotoWorkComment(models.Model):
    """照片展示评论（先发后审，通过后公开展示）。"""

    STATUS_PENDING = "待审核"
    STATUS_APPROVED = "已通过"
    STATUS_REJECTED = "已驳回"
    STATUS_CHOICES = (
        (STATUS_PENDING, "待审核"),
        (STATUS_APPROVED, "已通过"),
        (STATUS_REJECTED, "已驳回"),
    )

    comment_id = models.AutoField(primary_key=True, verbose_name="评论ID")
    photo_work = models.ForeignKey(
        PhotoWork,
        on_delete=models.CASCADE,
        related_name="comments",
        verbose_name="作品",
    )
    user_id = models.IntegerField(verbose_name="评论用户ID")
    content = models.TextField(max_length=2000, verbose_name="内容")
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        verbose_name="审核状态",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    class Meta:
        verbose_name = "作品评论"
        verbose_name_plural = "作品评论"
        ordering = ["-created_at"]


class RentalSchedule(models.Model):
    """租赁订单起租时间与租期（一单一件，与订单一对一）。"""

    schedule_id = models.AutoField(primary_key=True, verbose_name="主键ID")
    order = models.OneToOneField(
        Order,
        on_delete=models.CASCADE,
        related_name="rental_schedule",
        verbose_name="订单",
    )
    rental_start_time = models.DateTimeField(verbose_name="租赁开始时间")
    rental_days = models.IntegerField(verbose_name="租赁天数")


class HomeMarqueeSlide(models.Model):
    """首页横向跑马灯：图片与文案存库，可在 Django Admin 中维护。"""

    TRACK_FAST = 1
    TRACK_SLOW = 2
    TRACK_CHOICES = (
        (TRACK_FAST, "快轨（上行）"),
        (TRACK_SLOW, "慢轨（下行）"),
    )

    slide_id = models.AutoField(primary_key=True, verbose_name="条目ID")
    image_url = models.CharField(
        max_length=512,
        verbose_name="图片地址",
        help_text="可填完整 URL，或以 / 开头的站内路径（如 /images/xxx.jpg）",
    )
    title = models.CharField(max_length=120, verbose_name="主标题")
    subtitle = models.CharField(
        max_length=200, blank=True, default="", verbose_name="副标题/说明"
    )
    track = models.PositiveSmallIntegerField(
        choices=TRACK_CHOICES, default=TRACK_FAST, verbose_name="轨道"
    )
    sort_order = models.PositiveIntegerField(
        default=0, verbose_name="排序", help_text="同轨道内数字越小越靠前"
    )
    enabled = models.BooleanField(default=True, verbose_name="启用")

    class Meta:
        verbose_name = "首页跑马灯条目"
        verbose_name_plural = "首页跑马灯条目"
        ordering = ["track", "sort_order", "slide_id"]

    def __str__(self) -> str:
        return f"{self.title} ({self.get_track_display()})"


class BillingMessage(models.Model):
    """账单消息（无第三方支付，仅记录平台监管与结算说明）。"""

    KIND_DEBIT = "debit"
    KIND_CREDIT = "credit"

    message_id = models.AutoField(primary_key=True, verbose_name="消息ID")
    user_id = models.IntegerField(verbose_name="接收用户ID")
    order_id = models.IntegerField(null=True, blank=True, verbose_name="关联订单ID")
    key = models.CharField(max_length=96, unique=True, verbose_name="幂等键")
    kind = models.CharField(max_length=16, verbose_name="类型")
    amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="金额")
    remark = models.TextField(verbose_name="备注")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    class Meta:
        verbose_name = "账单消息"
        verbose_name_plural = "账单消息"
        ordering = ["-created_at"]
