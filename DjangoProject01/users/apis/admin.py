from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Dict, List

from django.db.models import Count, DateTimeField, F, Q, Sum
from django.db.models.functions import Coalesce, TruncDate
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from users import models
from users.apis.common import _equipment_to_dict, _get_json_body, _json_response, _require_admin
from users.apis.orders import _billing_message_to_dict, _order_to_dict


# ---------- Admin: users ----------


ADMIN_RESET_USER_PASSWORD = "123"


@require_http_methods(["GET"])
def api_admin_users(request):
    _, err = _require_admin(request)
    if err:
        return err
    qs = models.User.objects.all().order_by("-id")
    data = [
        {
            "id": u.id,
            "username": u.username,
            "phone": u.phone,
            "role": u.role,
            "status": u.status,
            "created_at": u.created_at.isoformat() if u.created_at else None,
        }
        for u in qs
    ]
    return _json_response(True, data=data)


@csrf_exempt
@require_http_methods(["POST"])
def api_admin_user_disable(request, user_id: int):
    admin, err = _require_admin(request)
    if err:
        return err
    body = _get_json_body(request)
    disabled = bool(body.get("disabled"))
    u = models.User.objects.filter(id=user_id).first()
    if not u:
        return _json_response(False, message="用户不存在", status=404)
    if u.id == admin.id and disabled:
        return _json_response(False, message="不能禁用自己的管理员账号", status=400)
    u.status = 0 if disabled else 1
    u.save(update_fields=["status"])
    if disabled:
        models.AuthToken.objects.filter(user=u).delete()
    return _json_response(True, data={"id": u.id, "status": u.status})


@csrf_exempt
@require_http_methods(["POST"])
def api_admin_user_reset_password(request, user_id: int):
    _, err = _require_admin(request)
    if err:
        return err
    u = models.User.objects.filter(id=user_id).first()
    if not u:
        return _json_response(False, message="用户不存在", status=404)
    u.set_password(ADMIN_RESET_USER_PASSWORD)
    u.save(update_fields=["password"])
    models.AuthToken.objects.filter(user=u).delete()
    return _json_response(True, message="密码已重置为 123", data={"id": u.id})


@csrf_exempt
@require_http_methods(["DELETE"])
def api_admin_user_delete(request, user_id: int):
    admin, err = _require_admin(request)
    if err:
        return err
    if admin.id == user_id:
        return _json_response(False, message="删除自己请用 /api/admin/me", status=400)
    u = models.User.objects.filter(id=user_id).first()
    if not u:
        return _json_response(False, message="用户不存在", status=404)
    models.AuthToken.objects.filter(user=u).delete()
    u.delete()
    return _json_response(True)


@csrf_exempt
@require_http_methods(["DELETE"])
def api_admin_me_delete(request):
    admin, err = _require_admin(request)
    if err:
        return err
    models.AuthToken.objects.filter(user=admin).delete()
    admin.delete()
    return _json_response(True)


@require_http_methods(["GET"])
def api_admin_dashboard_stats(request):
    """平台概览：注册用户数、商品数、已完成订单数、已完成订单总金额（管理员）。"""
    _, err = _require_admin(request)
    if err:
        return err
    user_count = models.User.objects.count()
    equipment_count = models.Equipment.objects.count()
    done_qs = models.Order.objects.filter(status="已完成")
    agg = done_qs.aggregate(
        completed_order_count=Count("order_id"),
        total_revenue=Sum("total_amount"),
    )
    rev = agg.get("total_revenue")
    if rev is None:
        rev = Decimal("0")
    else:
        rev = Decimal(str(rev)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    pending_equipment = models.Equipment.objects.filter(
        status=models.Equipment.STATUS_PENDING_REVIEW
    ).count()
    pending_works = models.PhotoWork.objects.filter(
        status=models.PhotoWork.STATUS_PENDING
    ).count()
    pending_comments = models.PhotoWorkComment.objects.filter(
        status=models.PhotoWorkComment.STATUS_PENDING
    ).count()

    today = timezone.localdate()
    start_day = today - timedelta(days=6)
    agg_rows = (
        models.Order.objects.filter(status="已完成")
        .annotate(
            eff_at=Coalesce(F("completed_at"), F("created_at"), output_field=DateTimeField()),
        )
        .annotate(day=TruncDate("eff_at"))
        .filter(day__gte=start_day, day__lte=today)
        .values("day")
        .annotate(count=Count("order_id"))
    )
    by_day: Dict[str, int] = {}
    for row in agg_rows:
        d = row["day"]
        if isinstance(d, datetime):
            ds = timezone.localtime(d).date().isoformat()
        elif isinstance(d, date):
            ds = d.isoformat()
        else:
            ds = str(d)[:10]
        by_day[ds] = int(row["count"])
    completed_orders_last_7_days: List[Dict[str, Any]] = []
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        ds = d.isoformat()
        completed_orders_last_7_days.append({"date": ds, "count": by_day.get(ds, 0)})

    data = {
        "user_count": user_count,
        "equipment_count": equipment_count,
        "completed_order_count": int(agg.get("completed_order_count") or 0),
        "total_revenue": str(rev),
        "pending": {
            "equipment": pending_equipment,
            "works": pending_works,
            "comments": pending_comments,
        },
        "completed_orders_last_7_days": completed_orders_last_7_days,
    }
    return _json_response(True, data=data)


# ---------- Admin: equipments ----------


@require_http_methods(["GET"])
def api_admin_equipments(request):
    _, err = _require_admin(request)
    if err:
        return err
    status = (request.GET.get("status") or "").strip()
    qs = models.Equipment.objects.all().order_by("-created_at")
    if status:
        qs = qs.filter(status=status)
    data = [_equipment_to_dict(eq, include_owner=True) for eq in qs]
    return _json_response(True, data=data)


@csrf_exempt
@require_http_methods(["POST"])
def api_admin_equipment_approve(request, equipment_id: int):
    _, err = _require_admin(request)
    if err:
        return err
    eq = models.Equipment.objects.filter(equipment_id=equipment_id).first()
    if not eq:
        return _json_response(False, message="商品不存在", status=404)
    if eq.status != models.Equipment.STATUS_PENDING_REVIEW:
        return _json_response(False, message="仅「待审核」商品可通过审核上架", status=400)
    eq.status = models.Equipment.STATUS_ON_SHELF
    eq.save(update_fields=["status"])
    return _json_response(True, data=_equipment_to_dict(eq, include_owner=True))


@csrf_exempt
@require_http_methods(["POST"])
def api_admin_equipment_reject(request, equipment_id: int):
    """管理员驳回商品上架申请（待审核 -> 已驳回）。"""
    _, err = _require_admin(request)
    if err:
        return err
    eq = models.Equipment.objects.filter(equipment_id=equipment_id).first()
    if not eq:
        return _json_response(False, message="商品不存在", status=404)
    if eq.status != models.Equipment.STATUS_PENDING_REVIEW:
        return _json_response(False, message="仅「待审核」商品可驳回", status=400)
    eq.status = models.Equipment.STATUS_REJECTED
    eq.save(update_fields=["status"])
    return _json_response(True, data=_equipment_to_dict(eq, include_owner=True))


@csrf_exempt
@require_http_methods(["POST"])
def api_admin_equipment_off_shelf(request, equipment_id: int):
    _, err = _require_admin(request)
    if err:
        return err
    eq = models.Equipment.objects.filter(equipment_id=equipment_id).first()
    if not eq:
        return _json_response(False, message="商品不存在", status=404)
    if eq.status != models.Equipment.STATUS_ON_SHELF:
        return _json_response(False, message="仅「已上架」商品可下架", status=400)
    eq.status = models.Equipment.STATUS_OFF
    eq.save(update_fields=["status"])
    return _json_response(True, data=_equipment_to_dict(eq, include_owner=True))


@csrf_exempt
@require_http_methods(["DELETE"])
def api_admin_equipment_delete(request, equipment_id: int):
    _, err = _require_admin(request)
    if err:
        return err
    eq = models.Equipment.objects.filter(equipment_id=equipment_id).first()
    if not eq:
        return _json_response(False, message="商品不存在", status=404)
    if eq.status not in (models.Equipment.STATUS_OFF, models.Equipment.STATUS_SOLD):
        return _json_response(False, message="仅「已下架」或「已卖出」的资源可删除", status=400)
    eq.delete()
    return _json_response(True)


# ---------- Admin: orders ----------


@require_http_methods(["GET"])
def api_admin_orders(request):
    """
    管理员查看全站订单（汇总）。
    支持 query: status, order_type(rent/sale), q(按订单id/买家id/卖家id 模糊)。
    """
    _, err = _require_admin(request)
    if err:
        return err
    status = (request.GET.get("status") or "").strip()
    order_type = (request.GET.get("order_type") or "").strip()
    q = (request.GET.get("q") or "").strip()

    qs = models.Order.objects.all().order_by("-created_at")
    if status:
        qs = qs.filter(status=status)
    if order_type:
        qs = qs.filter(order_type=order_type)
    if q:
        qs = qs.filter(Q(order_id__icontains=q) | Q(user_id__icontains=q) | Q(owner_id__icontains=q))

    buyer_map = {u.id: u for u in models.User.objects.filter(id__in=qs.values_list("user_id", flat=True))}
    owner_map = {u.id: u for u in models.User.objects.filter(id__in=qs.values_list("owner_id", flat=True))}

    data = []
    for o in qs[:500]:
        d = _order_to_dict(o)
        buyer = buyer_map.get(o.user_id)
        owner = owner_map.get(o.owner_id)
        d["buyer"] = (
            None
            if not buyer
            else {"id": buyer.id, "username": buyer.username, "phone": buyer.phone, "avatar_url": buyer.avatar_url}
        )
        d["owner"] = (
            None
            if not owner
            else {"id": owner.id, "username": owner.username, "phone": owner.phone, "avatar_url": owner.avatar_url}
        )
        data.append(d)
    return _json_response(True, data=data)


@require_http_methods(["GET"])
def api_admin_order_detail(request, order_id: int):
    _, err = _require_admin(request)
    if err:
        return err
    order = models.Order.objects.filter(order_id=order_id).first()
    if not order:
        return _json_response(False, message="订单不存在", status=404)
    d = _order_to_dict(order, detail=True)
    buyer = models.User.objects.filter(id=order.user_id).first()
    owner = models.User.objects.filter(id=order.owner_id).first()
    d["buyer"] = (
        None
        if not buyer
        else {"id": buyer.id, "username": buyer.username, "phone": buyer.phone, "avatar_url": buyer.avatar_url}
    )
    d["owner"] = (
        None
        if not owner
        else {"id": owner.id, "username": owner.username, "phone": owner.phone, "avatar_url": owner.avatar_url}
    )
    msgs = models.BillingMessage.objects.filter(order_id=order.order_id).order_by("created_at")
    d["billing_messages"] = [_billing_message_to_dict(m) for m in msgs]
    return _json_response(True, data=d)

