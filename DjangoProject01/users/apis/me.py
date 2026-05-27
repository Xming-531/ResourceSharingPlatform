import os
from uuid import uuid4

from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from users import models
from users.apis.common import (
    _get_json_body,
    _is_admin,
    _json_response,
    _parse_multipart,
    _require_user,
)


# ---------- Me ----------


@require_http_methods(["GET"])
def api_me(request):
    user, err = _require_user(request)
    if err:
        return err
    return _json_response(
        True,
        data={
            "id": user.id,
            "username": user.username,
            "phone": user.phone,
            "role": user.role,
            "status": user.status,
            "avatar_url": user.avatar_url,
            "identity_verified": bool(getattr(user, "identity_verified", False)),
        },
    )


@csrf_exempt
@require_http_methods(["PATCH"])
def api_me_avatar(request):
    user, err = _require_user(request)
    if err:
        return err
    is_multipart = (request.content_type or "").startswith("multipart/form-data")
    if not is_multipart:
        return _json_response(False, message="请使用 multipart/form-data 上传头像", status=400)
    _, files, parse_err = _parse_multipart(request)
    if parse_err:
        return parse_err
    if not files or not files.get("avatar"):
        return _json_response(False, message="缺少文件字段 avatar", status=400)
    f = files["avatar"]
    ext = os.path.splitext(getattr(f, "name", "") or "")[1].lower()[:10]
    if ext not in (".jpg", ".jpeg", ".png", ".webp", ".gif"):
        return _json_response(False, message="头像仅支持 jpg/jpeg/png/webp/gif", status=400)
    os.makedirs(settings.MEDIA_ROOT, exist_ok=True)
    filename = f"avatar_{user.id}_{uuid4().hex}{ext}"
    abs_path = os.path.join(str(settings.MEDIA_ROOT), filename)
    with open(abs_path, "wb") as out:
        for chunk in f.chunks():
            out.write(chunk)
    url = f"{settings.MEDIA_URL}{filename}"
    user.avatar_url = url
    user.save(update_fields=["avatar_url"])
    return _json_response(True, data={"avatar_url": user.avatar_url})


@csrf_exempt
@require_http_methods(["PATCH"])
def api_me_phone(request):
    user, err = _require_user(request)
    if err:
        return err
    body = _get_json_body(request)
    phone = (body.get("phone") or "").strip()
    if not phone:
        return _json_response(False, message="缺少参数：phone", status=400)
    user.phone = phone
    user.save(update_fields=["phone"])
    return _json_response(True, data={"phone": user.phone})


@csrf_exempt
@require_http_methods(["PATCH"])
def api_me_password(request):
    user, err = _require_user(request)
    if err:
        return err
    body = _get_json_body(request)
    old_password = body.get("old_password") or ""
    new_password = body.get("new_password") or ""
    if not old_password or not new_password:
        return _json_response(
            False, message="缺少参数：old_password/new_password", status=400
        )
    if not user.check_password(old_password):
        return _json_response(False, message="原密码错误", status=400)
    user.set_password(new_password)
    user.save(update_fields=["password"])
    # optional: logout all tokens for safety
    models.AuthToken.objects.filter(user=user).delete()
    return _json_response(True, message="密码已修改，请重新登录")


@csrf_exempt
@require_http_methods(["POST"])
def api_me_identity_verify(request):
    """模拟第三方实名：将当前用户标为已实名。"""
    user, err = _require_user(request)
    if err:
        return err
    if getattr(user, "identity_verified", False):
        return _json_response(True, data={"identity_verified": True}, message="您已完成实名认证")
    user.identity_verified = True
    user.save(update_fields=["identity_verified"])
    return _json_response(True, data={"identity_verified": True}, message="实名认证成功")


def _order_physical_delete_if_both_sides_hidden(order_id: int) -> None:
    """与 api_order_delete 一致：双方均已软删则从数据库移除订单及租赁日程。"""
    o = models.Order.objects.filter(order_id=order_id).first()
    if not o:
        return
    if getattr(o, "hidden_from_buyer", False) and getattr(o, "hidden_from_owner", False):
        o.delete()


def _apply_counterparty_order_hide_on_account_delete(user_id: int) -> None:
    """
    用户注销时：对其作为买方/卖方参与的订单，将「对方」列表中的该单标记为已删除（软删）。
    - 曾是买方：对出租方/卖家隐藏（hidden_from_owner）
    - 曾是卖方：对买方隐藏（hidden_from_buyer）
    若买卖双方此前都已软删，则物理删除订单。
    """
    buyer_ids = list(
        models.Order.objects.filter(user_id=user_id).values_list("order_id", flat=True)
    )
    for oid in buyer_ids:
        order = models.Order.objects.filter(order_id=oid).first()
        if not order:
            continue
        if not getattr(order, "hidden_from_owner", False):
            order.hidden_from_owner = True
            order.save(update_fields=["hidden_from_owner"])
        _order_physical_delete_if_both_sides_hidden(oid)
    owner_ids = list(
        models.Order.objects.filter(owner_id=user_id).values_list("order_id", flat=True)
    )
    for oid in owner_ids:
        order = models.Order.objects.filter(order_id=oid).first()
        if not order:
            continue
        if not getattr(order, "hidden_from_buyer", False):
            order.hidden_from_buyer = True
            order.save(update_fields=["hidden_from_buyer"])
        _order_physical_delete_if_both_sides_hidden(oid)


@csrf_exempt
@require_http_methods(["DELETE"])
def api_me_delete_account(request):
    """普通用户注销：清理其商品/作品/评论/账单/收藏；关联订单对端侧软删；再删 Token 与用户。"""
    user, err = _require_user(request)
    if err:
        return err
    if _is_admin(user):
        return _json_response(False, message="管理员请使用管理端提供的账号注销方式", status=400)
    if (
        models.Order.objects.filter(Q(user_id=user.id) | Q(owner_id=user.id))
        .exclude(status="已完成")
        .exists()
    ):
        return _json_response(False, message="存在未完成的订单，暂无法注销账户", status=400)

    uid = user.id
    with transaction.atomic():
        _apply_counterparty_order_hide_on_account_delete(uid)
        models.BillingMessage.objects.filter(user_id=uid).delete()
        models.Favorite.objects.filter(user_id=uid).delete()
        models.PhotoWorkComment.objects.filter(user_id=uid).delete()
        models.PhotoWork.objects.filter(user_id=uid).delete()
        models.Equipment.objects.filter(owner_id=uid).delete()
        models.AuthToken.objects.filter(user_id=uid).delete()
        user.delete()
    return _json_response(True, message="账户已注销")

