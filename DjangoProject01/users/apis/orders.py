from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal
import math
from typing import Any, Dict, List, Optional, Tuple

from django.db import transaction
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from users import models
from users.apis.common import (
    _datetime_to_iso,
    _effective_listing_type,
    _equipment_to_dict,
    _get_json_body,
    _json_response,
    _require_admin,
    _resolve_user,
)


# ---------- Orders & rental flow ----------


ORDER_RENT_PENDING_PICKUP = "待取货"
ORDER_RENT_ACTIVE = "租赁中"
ORDER_RENT_PENDING_RETURN = "待归还"
ORDER_RENT_DONE = "已完成"

ORDER_SALE_PENDING = "待交付"
ORDER_SALE_DONE = "已完成"

# 归还时间分档：距租期结束仍大于 N 小时仅「提前归还」；最后 N 小时内为「按时归还」；届满后「超期归还」进待归还
RETURN_ON_TIME_WINDOW_HOURS = 3


def _billing_amount_q2(x: Decimal) -> Decimal:
    return Decimal(x).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _billing_msg_ensure(
    *,
    order_id: Optional[int],
    key: str,
    user_id: int,
    kind: str,
    amount: Decimal,
    remark: str,
) -> None:
    if models.BillingMessage.objects.filter(key=key).exists():
        return
    models.BillingMessage.objects.create(
        user_id=user_id,
        order_id=order_id,
        key=key,
        kind=kind,
        amount=_billing_amount_q2(amount),
        remark=remark,
    )


def _emit_billing_checkout(order: models.Order) -> None:
    buyer = order.user_id
    amt = _billing_amount_q2(order.total_amount)
    oid = order.order_id
    if order.order_type == models.Order.TYPE_SALE:
        _billing_msg_ensure(
            order_id=oid,
            key=f"o{oid}_sale_buyer_deduct",
            user_id=buyer,
            kind=models.BillingMessage.KIND_DEBIT,
            amount=amt,
            remark="资金暂时存放在平台账户监管。",
        )
        return
    _billing_msg_ensure(
        order_id=oid,
        key=f"o{oid}_rent_buyer_deduct",
        user_id=buyer,
        kind=models.BillingMessage.KIND_DEBIT,
        amount=amt,
        remark="租金押金暂时存放在平台账户监管。",
    )


def _emit_billing_sale_complete(order: models.Order) -> None:
    if order.order_type != models.Order.TYPE_SALE or order.status != ORDER_SALE_DONE:
        return
    oid = order.order_id
    amt = _billing_amount_q2(order.total_amount)
    _billing_msg_ensure(
        order_id=oid,
        key=f"o{oid}_sale_owner_credit",
        user_id=order.owner_id,
        kind=models.BillingMessage.KIND_CREDIT,
        amount=amt,
        remark="本次交易金额已到账。",
    )


def _get_order_rental_schedule(order: models.Order) -> Optional[models.RentalSchedule]:
    return models.RentalSchedule.objects.filter(order_id=order.order_id).first()


def _compute_rent_settlement(
    order: models.Order, settled_at
) -> Tuple[Decimal, Decimal, str, str]:
    """归还完成时：租借方到账金额、出租方到账金额、双方备注。"""
    R = _billing_amount_q2(Decimal(str(order.subtotal)))
    D = _billing_amount_q2(Decimal(str(order.deposit_amount)))

    used_total = Decimal("0")
    late_fee_total = Decimal("0")

    price_i = Decimal(str(order.rental_price))
    sub_i = Decimal(str(order.subtotal))
    dep_i = Decimal(str(order.deposit_amount))
    s = _get_order_rental_schedule(order)
    if s:
        start_i = s.rental_start_time
        end_i = start_i + timedelta(days=int(s.rental_days))
    else:
        start_i = order.created_at
        end_i = start_i + timedelta(days=int(order.rental_days))

    sec_used = (settled_at - start_i).total_seconds()
    if sec_used <= 0:
        days_used = 1
    else:
        days_used = max(1, math.ceil(sec_used / 86400.0))
    used_money_i = min(Decimal(days_used) * price_i, sub_i)
    used_total += used_money_i

    if settled_at > end_i:
        sec_ot = (settled_at - end_i).total_seconds()
        if sec_ot > 0:
            ot_days = max(1, math.ceil(sec_ot / 86400.0))
            fee_i = min(Decimal(ot_days) * price_i, dep_i)
        else:
            fee_i = Decimal("0")
        late_fee_total += fee_i

    used_total = _billing_amount_q2(used_total)
    late_fee_total = _billing_amount_q2(late_fee_total)
    # 整单再封顶：扣款/结算侧「超期费用」不以负数形式向租借方追补，最多扣满已付押金总额
    if late_fee_total > D:
        late_fee_total = D

    if late_fee_total > 0:
        buyer_amt = _billing_amount_q2(D - late_fee_total)
        if buyer_amt < 0:
            buyer_amt = Decimal("0")
        owner_amt = _billing_amount_q2(R + late_fee_total)
        if buyer_amt <= 0:
            buyer_note = (
                "本次交易结算：超期使用费已按超期天数（自约定租期结束起算，按天向上取整）从押金扣除；"
                "扣费以已付押金总额为上限，故押金无余额可退（平台监管账户）。"
            )
        else:
            buyer_note = "本次交易结算：押金扣除超期使用费（按天向上取整，以押金总额为上限）后的余额已到账（平台监管账户）。"
        owner_note = "本次交易金额已到账（含约定租金及超期使用费；超期费按日租金×超期天数自押金结算，且不超过已付押金总额）。"
        return buyer_amt, owner_amt, buyer_note, owner_note

    if used_total + Decimal("0.005") < R:
        buyer_amt = _billing_amount_q2(D + (R - used_total))
        owner_amt = _billing_amount_q2(used_total)
        buyer_note = "本次交易提前归还结算：未使用租金与押金已退回（平台监管账户）。"
        owner_note = "本次交易金额已到账（按实际租用天数结算租金，不足一天按一天计）。"
        return buyer_amt, owner_amt, buyer_note, owner_note

    buyer_amt = D
    owner_amt = R
    buyer_note = "本次交易的押金已全额退回（平台监管账户）。"
    owner_note = "本次交易金额已到账（租期租金）。"
    return (
        _billing_amount_q2(buyer_amt),
        _billing_amount_q2(owner_amt),
        buyer_note,
        owner_note,
    )


def _emit_billing_rent_complete(order: models.Order) -> None:
    if order.order_type != models.Order.TYPE_RENT or order.status != ORDER_RENT_DONE:
        return
    oid = order.order_id
    settled_at = timezone.now()
    buyer_amt, owner_amt, buyer_note, owner_note = _compute_rent_settlement(order, settled_at)
    _billing_msg_ensure(
        order_id=oid,
        key=f"o{oid}_rent_buyer_credit",
        user_id=order.user_id,
        kind=models.BillingMessage.KIND_CREDIT,
        amount=buyer_amt,
        remark=buyer_note,
    )
    _billing_msg_ensure(
        order_id=oid,
        key=f"o{oid}_rent_owner_credit",
        user_id=order.owner_id,
        kind=models.BillingMessage.KIND_CREDIT,
        amount=owner_amt,
        remark=owner_note,
    )


def _billing_message_to_dict(m: models.BillingMessage) -> Dict[str, Any]:
    return {
        "message_id": m.message_id,
        "user_id": m.user_id,
        "order_id": m.order_id,
        "kind": m.kind,
        "amount": str(m.amount),
        "remark": m.remark,
        "created_at": m.created_at.isoformat() if m.created_at else None,
    }


def _contract_due_at(order: models.Order):
    """租赁订单约定到期：订单创建时间 + 租用天数（整日）。"""
    if order.order_type != models.Order.TYPE_RENT:
        return None
    days = max(1, int(order.rental_days))
    return order.created_at + timedelta(days=days)


def _rental_schedule_max_end(order: models.Order):
    """租赁日程上的约定结束时刻；无日程则为 None。"""
    s = _get_order_rental_schedule(order)
    if not s:
        return None
    return s.rental_start_time + timedelta(days=int(s.rental_days))


def _rental_period_end_datetime(order: models.Order):
    """与列表 rental_period_end_at 一致：优先租赁日程结束，否则合同到期。"""
    me = _rental_schedule_max_end(order)
    if me is not None:
        return me
    if order.order_type != models.Order.TYPE_RENT:
        return None
    return _contract_due_at(order)


def _hours_until_rental_end(order: models.Order) -> Optional[float]:
    """距离租期结束的小时数；已超期为负；无结束时刻为 None。"""
    end = _rental_period_end_datetime(order)
    if end is None:
        return None
    return (end - timezone.now()).total_seconds() / 3600.0


def _is_past_rental_end(order: models.Order) -> bool:
    """是否已达或超过约定租期结束（优先按租赁日程；无日程时按合同到期日）。"""
    if order.order_type != models.Order.TYPE_RENT:
        return False
    me = _rental_schedule_max_end(order)
    if me is not None:
        return timezone.now() >= me
    cd = _contract_due_at(order)
    return cd is not None and timezone.now() >= cd


def _early_return_allowed(order: models.Order) -> bool:
    """租赁中且未超期，且距结束仍大于 RETURN_ON_TIME_WINDOW_HOURS 小时。"""
    if order.order_type != models.Order.TYPE_RENT or order.status != ORDER_RENT_ACTIVE:
        return False
    if _is_past_rental_end(order):
        return False
    h = _hours_until_rental_end(order)
    if h is None:
        return False
    return h > RETURN_ON_TIME_WINDOW_HOURS


def _normal_return_allowed(order: models.Order) -> bool:
    """租赁中、未超期，且剩余时间在 (0, RETURN_ON_TIME_WINDOW_HOURS] 小时内（按时归还窗口）。"""
    if order.order_type != models.Order.TYPE_RENT or order.status != ORDER_RENT_ACTIVE:
        return False
    if _is_past_rental_end(order):
        return False
    h = _hours_until_rental_end(order)
    if h is None:
        return False
    return h > 0 and h <= RETURN_ON_TIME_WINDOW_HOURS


def _enter_pending_return(order: models.Order) -> None:
    order.status = ORDER_RENT_PENDING_RETURN
    order.buyer_return_ok = False
    order.owner_return_ok = False
    order.early_return_buyer_agreed = False
    order.early_return_owner_agreed = False
    order.normal_return_buyer_requested = False
    order.save(
        update_fields=[
            "status",
            "buyer_return_ok",
            "owner_return_ok",
            "early_return_buyer_agreed",
            "early_return_owner_agreed",
            "normal_return_buyer_requested",
        ]
    )


def _order_equipment_ids(order: models.Order) -> List[int]:
    if not order.equipment_id:
        return []
    return [order.equipment_id]


def _update_equipment_for_order_seller(order: models.Order, new_status: str) -> None:
    """仅更新本订单卖家名下的商品。"""
    eids = _order_equipment_ids(order)
    if not eids:
        return
    models.Equipment.objects.filter(equipment_id__in=eids, owner_id=order.owner_id).update(
        status=new_status
    )


def _sync_rental_expiry(order: models.Order) -> None:
    """超期后不自动进入「待归还」；清除已失效的按时归还与提前归还申请（由租借方点「超期归还」进入待归还）。"""
    if order.order_type != models.Order.TYPE_RENT or order.status != ORDER_RENT_ACTIVE:
        return
    if not _is_past_rental_end(order):
        return
    fields: List[str] = []
    if getattr(order, "normal_return_buyer_requested", False):
        order.normal_return_buyer_requested = False
        fields.append("normal_return_buyer_requested")
    if order.early_return_buyer_agreed or order.early_return_owner_agreed:
        order.early_return_buyer_agreed = False
        order.early_return_owner_agreed = False
        fields.extend(["early_return_buyer_agreed", "early_return_owner_agreed"])
    if fields:
        order.save(update_fields=fields)


def _finalize_if_handover_complete(order: models.Order) -> None:
    if not (order.owner_handover_ok and order.buyer_handover_ok):
        return
    if order.order_type == models.Order.TYPE_SALE:
        if order.status == ORDER_SALE_PENDING:
            order.status = ORDER_SALE_DONE
            order.completed_at = timezone.now()
            order.save(update_fields=["status", "completed_at"])
            # 出售完成：标记已卖出，不可再上架展示
            _update_equipment_for_order_seller(order, models.Equipment.STATUS_SOLD)
            order.refresh_from_db()
            _emit_billing_sale_complete(order)
        return
    if order.order_type == models.Order.TYPE_RENT:
        if order.status != ORDER_RENT_PENDING_PICKUP:
            return
        now = timezone.now()
        if not models.RentalSchedule.objects.filter(order_id=order.order_id).exists():
            models.RentalSchedule.objects.create(
                order=order,
                rental_start_time=now,
                rental_days=order.rental_days,
            )
        order.status = ORDER_RENT_ACTIVE
        order.save(update_fields=["status"])
        # 双方已交接、租期开始：商品进入租赁中（不公开展示）
        _update_equipment_for_order_seller(order, models.Equipment.STATUS_RENTING)


def _schedule_to_dict(s: models.RentalSchedule) -> Dict[str, Any]:
    return {
        "schedule_id": s.schedule_id,
        "order_id": s.order_id,
        "rental_start_time": _datetime_to_iso(s.rental_start_time),
        "rental_days": s.rental_days,
    }


def _order_user_party(u: Optional[models.User]) -> Optional[Dict[str, Any]]:
    if u is None:
        return None
    return {
        "id": u.id,
        "username": u.username,
        "phone": u.phone,
        "avatar_url": getattr(u, "avatar_url", None) or None,
    }


def _order_line_to_dict(
    order: models.Order, equipment_dict: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """一单一件：接口仍返回 items 数组（单元素），order_item_id 用订单号兼容旧前端。"""
    d: Dict[str, Any] = {
        "order_item_id": order.order_id,
        "order_id": order.order_id,
        "equipment_id": order.equipment_id,
        "rental_days": order.rental_days,
        "rental_price": str(order.rental_price),
        "subtotal": str(order.subtotal),
        "deposit_amount": str(order.deposit_amount),
        "created_at": _datetime_to_iso(order.created_at),
    }
    if equipment_dict is not None:
        d["equipment"] = equipment_dict
    return d


def _order_to_dict(order: models.Order, *, detail: bool = False) -> Dict[str, Any]:
    _sync_rental_expiry(order)
    order.refresh_from_db()
    d: Dict[str, Any] = {
        "order_id": order.order_id,
        "user_id": order.user_id,
        "owner_id": order.owner_id,
        "order_type": order.order_type,
        "total_amount": str(order.total_amount),
        "status": order.status,
        "shipping_address": order.shipping_address,
        "contact_phone": order.contact_phone,
        "owner_handover_ok": order.owner_handover_ok,
        "buyer_handover_ok": order.buyer_handover_ok,
        "owner_return_ok": order.owner_return_ok,
        "buyer_return_ok": getattr(order, "buyer_return_ok", False),
        "created_at": _datetime_to_iso(order.created_at),
    }
    cd = _contract_due_at(order) if order.order_type == models.Order.TYPE_RENT else None
    d["contract_due_at"] = _datetime_to_iso(cd)
    d["normal_return_allowed"] = _normal_return_allowed(order)
    d["normal_return_buyer_requested"] = bool(getattr(order, "normal_return_buyer_requested", False))
    d["early_return_allowed"] = _early_return_allowed(order)
    d["rental_overdue"] = False
    if order.order_type == models.Order.TYPE_RENT and order.status in (ORDER_RENT_ACTIVE, ORDER_RENT_PENDING_RETURN):
        d["rental_overdue"] = _is_past_rental_end(order)
    d["hours_until_rental_end"] = None
    d["overdue_seconds"] = 0
    if order.order_type == models.Order.TYPE_RENT:
        h_left = _hours_until_rental_end(order)
        d["hours_until_rental_end"] = None if h_left is None else round(h_left, 4)
        if _is_past_rental_end(order):
            end_dt = _rental_period_end_datetime(order)
            if end_dt is not None:
                d["overdue_seconds"] = max(0, int((timezone.now() - end_dt).total_seconds()))
    d["early_return_buyer_agreed"] = bool(getattr(order, "early_return_buyer_agreed", False))
    d["early_return_owner_agreed"] = bool(getattr(order, "early_return_owner_agreed", False))
    sched_list: List[models.RentalSchedule] = []
    if order.order_type == models.Order.TYPE_RENT:
        rs = _get_order_rental_schedule(order)
        if rs:
            sched_list = [rs]
    if sched_list:
        ends = [s.rental_start_time + timedelta(days=int(s.rental_days)) for s in sched_list]
        d["rental_period_end_at"] = _datetime_to_iso(max(ends))
    else:
        d["rental_period_end_at"] = _datetime_to_iso(cd) if order.order_type == models.Order.TYPE_RENT else None
    if detail:
        eq = models.Equipment.objects.filter(equipment_id=order.equipment_id).first()
        eq_dict = _equipment_to_dict(eq, include_owner=True) if eq else None
        d["items"] = [_order_line_to_dict(order, eq_dict)]
        d["rental_schedules"] = [_schedule_to_dict(s) for s in sched_list]
        buyer_u = models.User.objects.filter(id=order.user_id).first()
        owner_u = models.User.objects.filter(id=order.owner_id).first()
        d["buyer"] = _order_user_party(buyer_u)
        d["owner"] = _order_user_party(owner_u)
    return d


def _get_order_for_user(
    order_id: int, user: models.User
) -> Tuple[Optional[models.Order], Optional[JsonResponse]]:
    """买方/卖方若已对本订单软删，则不可再查看详情。"""
    order = models.Order.objects.filter(order_id=order_id).first()
    if not order:
        return None, _json_response(False, message="订单不存在", status=404)
    if user.id not in (order.user_id, order.owner_id):
        return None, _json_response(False, message="无权限查看该订单", status=403)
    if user.id == order.user_id and getattr(order, "hidden_from_buyer", False):
        return None, _json_response(False, message="订单不存在", status=404)
    if user.id == order.owner_id and getattr(order, "hidden_from_owner", False):
        return None, _json_response(False, message="订单不存在", status=404)
    return order, None


@csrf_exempt
@require_http_methods(["POST"])
def api_order_checkout(request):
    user, err = _resolve_user(request)
    if err:
        return err
    if not getattr(user, "identity_verified", False):
        return _json_response(
            False,
            message="请先完成实名认证后再下单，请前往「个人信息」进行实名",
            status=403,
        )
    body = _get_json_body(request)
    items_in = body.get("items")
    if not isinstance(items_in, list) or not items_in:
        return _json_response(False, message="缺少 items", status=400)
    addr = (body.get("shipping_address") or "").strip()
    phone = (body.get("contact_phone") or "").strip()
    if not addr or not phone:
        return _json_response(False, message="缺少收货地址或联系电话", status=400)

    created_orders: List[Dict[str, Any]] = []

    try:
        with transaction.atomic():
            for raw in items_in:
                if not isinstance(raw, dict):
                    return _json_response(False, message="items 格式错误", status=400)
                eid = int(raw.get("equipment_id"))
                days = int(raw.get("rental_days", 1))
                eq = (
                    models.Equipment.objects.select_for_update()
                    .filter(equipment_id=eid, status=models.Equipment.STATUS_ON_SHELF)
                    .first()
                )
                if not eq:
                    return _json_response(False, message=f"商品不可用: {eid}", status=400)
                if eq.owner_id == user.id:
                    return _json_response(False, message="不能下单自己的商品", status=400)
                lt = _effective_listing_type(eq)

                price = Decimal(str(eq.price))
                dep = Decimal(str(eq.deposit))

                if lt == models.Equipment.LISTING_SALE:
                    days = 1
                    subtotal = price
                    dep_line = Decimal("0")
                else:
                    if days < 1:
                        return _json_response(False, message="租期至少 1 天", status=400)
                    subtotal = price * Decimal(days)
                    dep_line = dep

                line_total = subtotal + dep_line
                ot = models.Order.TYPE_RENT if lt == models.Equipment.LISTING_RENT else models.Order.TYPE_SALE
                init_status = ORDER_RENT_PENDING_PICKUP if ot == models.Order.TYPE_RENT else ORDER_SALE_PENDING

                order = models.Order.objects.create(
                    user_id=user.id,
                    owner_id=eq.owner_id,
                    order_type=ot,
                    total_amount=line_total,
                    status=init_status,
                    shipping_address=addr,
                    contact_phone=phone,
                    equipment_id=eq.equipment_id,
                    rental_days=days,
                    rental_price=price,
                    subtotal=subtotal,
                    deposit_amount=dep_line,
                )
                eq_status = (
                    models.Equipment.STATUS_PENDING_DELIVERY
                    if ot == models.Order.TYPE_SALE
                    else models.Equipment.STATUS_PENDING_PICKUP
                )
                models.Equipment.objects.filter(equipment_id=eq.equipment_id).update(status=eq_status)
                order.refresh_from_db()
                _emit_billing_checkout(order)
                created_orders.append(_order_to_dict(order, detail=True))
    except (TypeError, ValueError):
        return _json_response(False, message="参数格式错误", status=400)

    return _json_response(True, data={"orders": created_orders, "order_ids": [o["order_id"] for o in created_orders]})


@require_http_methods(["GET"])
def api_my_orders(request):
    user, err = _resolve_user(request)
    if err:
        return err
    qs = models.Order.objects.filter(user_id=user.id, hidden_from_buyer=False).order_by("-created_at")
    return _json_response(True, data=[_order_to_dict(o) for o in qs])


@require_http_methods(["GET"])
def api_my_sales_orders(request):
    user, err = _resolve_user(request)
    if err:
        return err
    qs = models.Order.objects.filter(owner_id=user.id, hidden_from_owner=False).order_by("-created_at")
    orders = list(qs)
    buyer_ids = {o.user_id for o in orders}
    buyer_map = {u.id: u for u in models.User.objects.filter(id__in=buyer_ids)}
    data: List[Dict[str, Any]] = []
    for o in orders:
        d = _order_to_dict(o)
        d["buyer"] = _order_user_party(buyer_map.get(o.user_id))
        data.append(d)
    return _json_response(True, data=data)


@require_http_methods(["GET"])
def api_my_billing_messages(request):
    user, err = _resolve_user(request)
    if err:
        return err
    qs = models.BillingMessage.objects.filter(user_id=user.id).order_by("-created_at")[:500]
    return _json_response(True, data=[_billing_message_to_dict(m) for m in qs])


@csrf_exempt
@require_http_methods(["DELETE"])
def api_my_billing_message_delete(request, message_id: int):
    user, err = _resolve_user(request)
    if err:
        return err
    m = models.BillingMessage.objects.filter(message_id=message_id, user_id=user.id).first()
    if not m:
        return _json_response(False, message="消息不存在或无权删除", status=404)
    m.delete()
    return _json_response(True)


@require_http_methods(["GET"])
def api_order_detail(request, order_id: int):
    user, err = _resolve_user(request)
    if err:
        return err
    order, oerr = _get_order_for_user(order_id, user)
    if oerr:
        return oerr
    return _json_response(True, data=_order_to_dict(order, detail=True))


@csrf_exempt
@require_http_methods(["POST"])
def api_order_confirm_handover_owner(request, order_id: int):
    user, err = _resolve_user(request)
    if err:
        return err
    order = models.Order.objects.filter(order_id=order_id).first()
    if not order:
        return _json_response(False, message="订单不存在", status=404)
    if order.owner_id != user.id:
        return _json_response(False, message="仅设备拥有者可确认", status=403)
    if order.order_type == models.Order.TYPE_RENT:
        if order.status != ORDER_RENT_PENDING_PICKUP:
            return _json_response(False, message="当前状态不可由卖家确认取货", status=400)
    elif order.order_type == models.Order.TYPE_SALE:
        if order.status != ORDER_SALE_PENDING:
            return _json_response(False, message="当前状态不可由卖家确认交付", status=400)
    else:
        return _json_response(False, message="未知订单类型", status=400)
    order.owner_handover_ok = True
    order.save(update_fields=["owner_handover_ok"])
    _finalize_if_handover_complete(order)
    order.refresh_from_db()
    return _json_response(True, data=_order_to_dict(order, detail=True))


@csrf_exempt
@require_http_methods(["POST"])
def api_order_confirm_handover_buyer(request, order_id: int):
    user, err = _resolve_user(request)
    if err:
        return err
    order = models.Order.objects.filter(order_id=order_id).first()
    if not order:
        return _json_response(False, message="订单不存在", status=404)
    if order.user_id != user.id:
        return _json_response(False, message="仅下单用户可确认", status=403)
    if order.order_type == models.Order.TYPE_RENT:
        if order.status != ORDER_RENT_PENDING_PICKUP:
            return _json_response(False, message="当前状态不可由买家确认取货", status=400)
    elif order.order_type == models.Order.TYPE_SALE:
        if order.status != ORDER_SALE_PENDING:
            return _json_response(False, message="当前状态不可由买家确认收货", status=400)
    if not order.owner_handover_ok:
        return _json_response(
            False,
            message="请待出租方/卖方先确认交接后，您再确认取货/收货",
            status=400,
        )
    order.buyer_handover_ok = True
    order.save(update_fields=["buyer_handover_ok"])
    _finalize_if_handover_complete(order)
    order.refresh_from_db()
    return _json_response(True, data=_order_to_dict(order, detail=True))


@csrf_exempt
@require_http_methods(["POST"])
def api_order_confirm_return_owner(request, order_id: int):
    user, err = _resolve_user(request)
    if err:
        return err
    order = models.Order.objects.filter(order_id=order_id).first()
    if not order:
        return _json_response(False, message="订单不存在", status=404)
    if order.owner_id != user.id:
        return _json_response(False, message="仅设备拥有者可确认归还完成", status=403)
    if order.order_type != models.Order.TYPE_RENT or order.status != ORDER_RENT_PENDING_RETURN:
        return _json_response(False, message="仅「待归还」的租赁订单可由卖家确认完成", status=400)
    order.owner_return_ok = True
    if getattr(order, "buyer_return_ok", False):
        order.status = ORDER_RENT_DONE
        order.completed_at = timezone.now()
        order.save(update_fields=["owner_return_ok", "status", "completed_at"])
        # 归还完成：自动进入待审核，管理员通过后重新上架展示
        _update_equipment_for_order_seller(order, models.Equipment.STATUS_PENDING_REVIEW)
        order.refresh_from_db()
        _emit_billing_rent_complete(order)
    else:
        order.save(update_fields=["owner_return_ok"])
    return _json_response(True, data=_order_to_dict(order, detail=True))


@csrf_exempt
@require_http_methods(["POST"])
def api_order_confirm_return_buyer(request, order_id: int):
    user, err = _resolve_user(request)
    if err:
        return err
    order = models.Order.objects.filter(order_id=order_id).first()
    if not order:
        return _json_response(False, message="订单不存在", status=404)
    if order.user_id != user.id:
        return _json_response(False, message="仅下单用户可确认归还", status=403)
    if order.order_type != models.Order.TYPE_RENT or order.status != ORDER_RENT_PENDING_RETURN:
        return _json_response(False, message="仅「待归还」的租赁订单可确认归还", status=400)
    if not hasattr(order, "buyer_return_ok"):
        return _json_response(False, message="订单表缺少 buyer_return_ok 字段，请先迁移数据库", status=500)
    order.buyer_return_ok = True
    if order.owner_return_ok:
        order.status = ORDER_RENT_DONE
        order.completed_at = timezone.now()
        order.save(update_fields=["buyer_return_ok", "status", "completed_at"])
        _update_equipment_for_order_seller(order, models.Equipment.STATUS_PENDING_REVIEW)
        order.refresh_from_db()
        _emit_billing_rent_complete(order)
    else:
        order.save(update_fields=["buyer_return_ok"])
    return _json_response(True, data=_order_to_dict(order, detail=True))


@csrf_exempt
@require_http_methods(["POST"])
def api_order_early_return(request, order_id: int):
    """租借方申请提前归还；出租方同意后双方均确认，再进入「待归还」。"""
    user, err = _resolve_user(request)
    if err:
        return err
    order = models.Order.objects.filter(order_id=order_id).first()
    if not order:
        return _json_response(False, message="订单不存在", status=404)
    if order.user_id != user.id:
        return _json_response(False, message="仅租借方可申请提前归还", status=403)
    if order.order_type != models.Order.TYPE_RENT or order.status != ORDER_RENT_ACTIVE:
        return _json_response(False, message="仅「租赁中」订单可申请提前归还", status=400)
    if _is_past_rental_end(order):
        return _json_response(False, message="租期已届满，请使用「超期归还」进入待归还流程", status=400)
    if not order.early_return_buyer_agreed:
        if not _early_return_allowed(order):
            return _json_response(
                False,
                message=f"距离租期结束已不足{RETURN_ON_TIME_WINDOW_HOURS}小时，请使用「按时归还」",
                status=400,
            )
        order.early_return_buyer_agreed = True
        order.normal_return_buyer_requested = False
        if order.early_return_owner_agreed:
            _enter_pending_return(order)
        else:
            order.save(update_fields=["early_return_buyer_agreed", "normal_return_buyer_requested"])
    order.refresh_from_db()
    return _json_response(True, data=_order_to_dict(order, detail=True))


@csrf_exempt
@require_http_methods(["POST"])
def api_order_early_return_owner(request, order_id: int):
    """出租方同意提前归还；须租借方已先申请，双方均确认后进入「待归还」。"""
    user, err = _resolve_user(request)
    if err:
        return err
    order = models.Order.objects.filter(order_id=order_id).first()
    if not order:
        return _json_response(False, message="订单不存在", status=404)
    if order.owner_id != user.id:
        return _json_response(False, message="仅出租方可同意提前归还", status=403)
    if order.order_type != models.Order.TYPE_RENT or order.status != ORDER_RENT_ACTIVE:
        return _json_response(False, message="仅「租赁中」订单可操作提前归还", status=400)
    if _is_past_rental_end(order):
        return _json_response(False, message="租期已届满，请使用「超期归还」进入待归还流程", status=400)
    if not order.early_return_buyer_agreed:
        return _json_response(False, message="请待租借方先申请提前归还", status=400)
    if not order.early_return_owner_agreed:
        order.early_return_owner_agreed = True
        if order.early_return_buyer_agreed:
            _enter_pending_return(order)
        else:
            order.save(update_fields=["early_return_owner_agreed"])
    order.refresh_from_db()
    return _json_response(True, data=_order_to_dict(order, detail=True))


@csrf_exempt
@require_http_methods(["POST"])
def api_order_early_return_owner_reject(request, order_id: int):
    """出租方驳回租借方的提前归还申请；驳回后 early_return_buyer_agreed 清零，租借方可再次申请。"""
    user, err = _resolve_user(request)
    if err:
        return err
    order = models.Order.objects.filter(order_id=order_id).first()
    if not order:
        return _json_response(False, message="订单不存在", status=404)
    if order.owner_id != user.id:
        return _json_response(False, message="仅出租方可驳回提前归还申请", status=403)
    if order.order_type != models.Order.TYPE_RENT or order.status != ORDER_RENT_ACTIVE:
        return _json_response(False, message="仅「租赁中」订单可驳回提前归还申请", status=400)
    if not order.early_return_buyer_agreed:
        return _json_response(False, message="当前无待处理的提前归还申请", status=400)
    if order.early_return_owner_agreed:
        return _json_response(False, message="您已同意该申请，无法驳回", status=400)
    order.early_return_buyer_agreed = False
    order.early_return_owner_agreed = False
    order.save(update_fields=["early_return_buyer_agreed", "early_return_owner_agreed"])
    order.refresh_from_db()
    return _json_response(True, data=_order_to_dict(order, detail=True))


def _complete_rent_order_on_time_return(order: models.Order) -> None:
    """按时归还由出租方确认后：直接完成订单并结算，不经过「待归还」。"""
    order.status = ORDER_RENT_DONE
    order.completed_at = timezone.now()
    order.buyer_return_ok = True
    order.owner_return_ok = True
    order.normal_return_buyer_requested = False
    order.save(
        update_fields=[
            "status",
            "completed_at",
            "buyer_return_ok",
            "owner_return_ok",
            "normal_return_buyer_requested",
        ]
    )
    _update_equipment_for_order_seller(order, models.Equipment.STATUS_PENDING_REVIEW)
    order.refresh_from_db()
    _emit_billing_rent_complete(order)


@csrf_exempt
@require_http_methods(["POST"])
def api_order_request_normal_return(request, order_id: int):
    """租借方在租期届满前 N 小时内发起按时归还；出租方确认后直接完成订单。"""
    user, err = _resolve_user(request)
    if err:
        return err
    order = models.Order.objects.filter(order_id=order_id).first()
    if not order:
        return _json_response(False, message="订单不存在", status=404)
    if order.user_id != user.id:
        return _json_response(False, message="仅租借方可发起按时归还", status=403)
    if order.order_type != models.Order.TYPE_RENT or order.status != ORDER_RENT_ACTIVE:
        return _json_response(False, message="仅「租赁中」订单可发起按时归还", status=400)
    if _is_past_rental_end(order):
        return _json_response(False, message="租期已届满，请使用「超期归还」进入待归还流程", status=400)
    if not _normal_return_allowed(order):
        return _json_response(
            False,
            message=(
                f"仅在租期结束前最后{RETURN_ON_TIME_WINDOW_HOURS}小时内可发起按时归还；"
                f"早于此时请用「提前归还」，已届满请用「超期归还」"
            ),
            status=400,
        )
    if order.normal_return_buyer_requested:
        order.refresh_from_db()
        return _json_response(True, data=_order_to_dict(order, detail=True))
    order.normal_return_buyer_requested = True
    order.early_return_buyer_agreed = False
    order.early_return_owner_agreed = False
    order.save(
        update_fields=[
            "normal_return_buyer_requested",
            "early_return_buyer_agreed",
            "early_return_owner_agreed",
        ]
    )
    order.refresh_from_db()
    return _json_response(True, data=_order_to_dict(order, detail=True))


@csrf_exempt
@require_http_methods(["POST"])
def api_order_confirm_normal_return_owner(request, order_id: int):
    """出租方确认租借方发起的按时归还：订单直接完成并结算。"""
    user, err = _resolve_user(request)
    if err:
        return err
    with transaction.atomic():
        order = models.Order.objects.select_for_update().filter(order_id=order_id).first()
        if not order:
            return _json_response(False, message="订单不存在", status=404)
        if order.owner_id != user.id:
            return _json_response(False, message="仅出租方可确认按时归还", status=403)
        if order.order_type != models.Order.TYPE_RENT or order.status != ORDER_RENT_ACTIVE:
            return _json_response(False, message="仅「租赁中」且租借方已发起按时归还时可确认", status=400)
        if not getattr(order, "normal_return_buyer_requested", False):
            return _json_response(False, message="请待租借方先发起按时归还", status=400)
        if _is_past_rental_end(order):
            return _json_response(False, message="租期已届满，请双方通过「待归还」确认归还", status=400)
        _complete_rent_order_on_time_return(order)
    order.refresh_from_db()
    return _json_response(True, data=_order_to_dict(order, detail=True))


@csrf_exempt
@require_http_methods(["POST"])
def api_order_request_overdue_return(request, order_id: int):
    """租借方：已超期时进入「待归还」，双方再确认归还后结算（含超期扣费）。"""
    user, err = _resolve_user(request)
    if err:
        return err
    order = models.Order.objects.filter(order_id=order_id).first()
    if not order:
        return _json_response(False, message="订单不存在", status=404)
    if order.user_id != user.id:
        return _json_response(False, message="仅租借方可发起超期归还", status=403)
    if order.order_type != models.Order.TYPE_RENT or order.status != ORDER_RENT_ACTIVE:
        return _json_response(False, message="仅「租赁中」且已超期的订单可发起超期归还", status=400)
    if not _is_past_rental_end(order):
        return _json_response(False, message="尚未超期，请使用提前归还或按时归还", status=400)
    _enter_pending_return(order)
    order.refresh_from_db()
    return _json_response(True, data=_order_to_dict(order, detail=True))


@csrf_exempt
@require_http_methods(["DELETE"])
def api_order_delete(request, order_id: int):
    """买家或卖家删除「已完成」订单：本方仅软删；双方都删后物理删除订单及租赁日程等。"""
    user, err = _resolve_user(request)
    if err:
        return err
    with transaction.atomic():
        order = models.Order.objects.select_for_update().filter(order_id=order_id).first()
        if not order:
            return _json_response(False, message="订单不存在", status=404)
        if user.id not in (order.user_id, order.owner_id):
            return _json_response(False, message="无权限操作该订单", status=403)
        if order.status not in (ORDER_RENT_DONE, ORDER_SALE_DONE):
            return _json_response(False, message="仅已完成的订单可删除", status=400)
        if user.id == order.user_id:
            if getattr(order, "hidden_from_buyer", False):
                return _json_response(False, message="您已从列表中移除该订单", status=400)
            order.hidden_from_buyer = True
        else:
            if getattr(order, "hidden_from_owner", False):
                return _json_response(False, message="您已从列表中移除该订单", status=400)
            order.hidden_from_owner = True
        if order.hidden_from_buyer and order.hidden_from_owner:
            order.delete()
        else:
            uf = ["hidden_from_buyer"] if user.id == order.user_id else ["hidden_from_owner"]
            order.save(update_fields=uf)
    return _json_response(True)


@csrf_exempt
@require_http_methods(["DELETE"])
def api_admin_order_delete(request, order_id: int):
    _, err = _require_admin(request)
    if err:
        return err
    order = models.Order.objects.filter(order_id=order_id).first()
    if not order:
        return _json_response(False, message="订单不存在", status=404)
    if order.status not in (ORDER_RENT_DONE, ORDER_SALE_DONE):
        return _json_response(False, message="仅已完成的订单可删除", status=400)
    with transaction.atomic():
        order.delete()
    return _json_response(True)

