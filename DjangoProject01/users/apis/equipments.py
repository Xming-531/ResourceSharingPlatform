import os
from uuid import uuid4

from django.conf import settings
from django.db.models import F, Q
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from users import models
from users.apis.common import (
    _equipment_to_dict,
    _get_json_body,
    _json_response,
    _multipart_post_or_parse,
    _optional_user,
    _parse_multipart,
    _require_user,
)


# ---------- Public equipments (index) ----------


@csrf_exempt
@require_http_methods(["POST"])
def api_equipment_view(request, equipment_id: int):
    """浏览量 +1。"""
    eq = models.Equipment.objects.filter(equipment_id=equipment_id).first()
    if not eq:
        return _json_response(False, message="商品不存在", status=404)
    models.Equipment.objects.filter(equipment_id=equipment_id).update(
        view_count=F("view_count") + 1
    )
    eq.refresh_from_db(fields=["view_count"])
    return _json_response(True, data={"equipment_id": equipment_id, "view_count": eq.view_count})


@require_http_methods(["GET"])
def api_equipments_public(request):
    qs = models.Equipment.objects.filter(status=models.Equipment.STATUS_ON_SHELF)
    q = (request.GET.get("q") or "").strip()
    if q:
        qs = qs.filter(Q(brand__icontains=q) | Q(model__icontains=q))
    me = _optional_user(request)
    if me is not None:
        qs = qs.exclude(owner_id=me.id)
    qs = qs.order_by("-created_at")
    favorite_ids: set = set()
    if me is not None:
        favorite_ids = set(
            models.Favorite.objects.filter(user_id=me.id).values_list("equipment_id", flat=True)
        )
    data = [
        _equipment_to_dict(
            eq,
            include_owner=True,
            is_favorited=(eq.equipment_id in favorite_ids) if me is not None else False,
        )
        for eq in qs
    ]
    return _json_response(True, data=data)


# ---------- User equipments ----------


@csrf_exempt
@require_http_methods(["POST"])
def api_equipment_create(request):
    user, err = _require_user(request)
    if err:
        return err
    is_multipart = (request.content_type or "").startswith("multipart/form-data")
    files = None
    if is_multipart:
        body, files, parse_err = _multipart_post_or_parse(request)
        if parse_err:
            return parse_err
    else:
        body = _get_json_body(request)

    cover_url = None
    if is_multipart and files and files.get("cover"):
        f = files["cover"]
        ext = os.path.splitext(getattr(f, "name", "") or "")[1].lower()[:10]
        if ext not in (".jpg", ".jpeg", ".png", ".webp", ".gif"):
            return _json_response(False, message="封面仅支持 jpg/jpeg/png/webp/gif", status=400)
        os.makedirs(settings.MEDIA_ROOT, exist_ok=True)
        filename = f"{uuid4().hex}{ext}"
        abs_path = os.path.join(str(settings.MEDIA_ROOT), filename)
        with open(abs_path, "wb") as out:
            for chunk in f.chunks():
                out.write(chunk)
        cover_url = f"{settings.MEDIA_URL}{filename}"
    required = ["title", "category", "brand", "model", "description", "price", "deposit", "location"]
    missing = [k for k in required if not (body.get(k) or "").__str__().strip()]
    if missing:
        return _json_response(False, message=f"缺少参数：{','.join(missing)}", status=400)
    cat = str(body["category"]).strip()
    if cat == "出售":
        listing_type = models.Equipment.LISTING_SALE
    elif cat == "出租":
        listing_type = models.Equipment.LISTING_RENT
    else:
        listing_type = (body.get("listing_type") or models.Equipment.LISTING_RENT).__str__().strip()
        if listing_type not in (models.Equipment.LISTING_RENT, models.Equipment.LISTING_SALE):
            return _json_response(False, message="listing_type 无效，应为 rent 或 sale", status=400)
    eq = models.Equipment.objects.create(
        owner_id=user.id,
        title=str(body["title"]).strip(),
        category=cat,
        brand=str(body["brand"]).strip(),
        model=str(body["model"]).strip(),
        description=str(body["description"]).strip(),
        listing_type=listing_type,
        price=body["price"],
        deposit=body["deposit"],
        cover_img_url=cover_url or (body.get("cover_img_url") or None),
        status=models.Equipment.STATUS_PENDING_REVIEW,
        location=str(body["location"]).strip(),
        view_count=0,
    )
    return _json_response(True, data=_equipment_to_dict(eq))


@require_http_methods(["GET"])
def api_my_equipments(request):
    user, err = _require_user(request)
    if err:
        return err
    qs = models.Equipment.objects.filter(owner_id=user.id).order_by("-created_at")
    return _json_response(True, data=[_equipment_to_dict(eq) for eq in qs])


@csrf_exempt
@require_http_methods(["PATCH"])
def api_my_equipment_update(request, equipment_id: int):
    user, err = _require_user(request)
    if err:
        return err
    eq = models.Equipment.objects.filter(equipment_id=equipment_id, owner_id=user.id).first()
    if not eq:
        return _json_response(False, message="商品不存在或无权限", status=404)
    if eq.status in (
        models.Equipment.STATUS_PENDING_DELIVERY,
        models.Equipment.STATUS_PENDING_PICKUP,
        models.Equipment.STATUS_RENTING,
        models.Equipment.STATUS_SOLD,
    ):
        return _json_response(False, message="订单进行中或已售出，暂不可编辑", status=400)
    is_multipart = (request.content_type or "").startswith("multipart/form-data")
    files = None
    if is_multipart:
        body, files, parse_err = _parse_multipart(request)
        if parse_err:
            return parse_err
    else:
        body = _get_json_body(request)

    cover_url = None
    if is_multipart and files and files.get("cover"):
        f = files["cover"]
        ext = os.path.splitext(getattr(f, "name", "") or "")[1].lower()[:10]
        if ext not in (".jpg", ".jpeg", ".png", ".webp", ".gif"):
            return _json_response(False, message="封面仅支持 jpg/jpeg/png/webp/gif", status=400)
        os.makedirs(settings.MEDIA_ROOT, exist_ok=True)
        filename = f"{uuid4().hex}{ext}"
        abs_path = os.path.join(str(settings.MEDIA_ROOT), filename)
        with open(abs_path, "wb") as out:
            for chunk in f.chunks():
                out.write(chunk)
        cover_url = f"{settings.MEDIA_URL}{filename}"

    if "listing_type" in body:
        lt = str(body["listing_type"]).strip()
        if lt not in (models.Equipment.LISTING_RENT, models.Equipment.LISTING_SALE):
            return _json_response(False, message="listing_type 无效，应为 rent 或 sale", status=400)

    updatable = [
        "title",
        "category",
        "brand",
        "model",
        "description",
        "price",
        "deposit",
        "location",
        "cover_img_url",
        "listing_type",
    ]
    changed = False
    for k in updatable:
        if k in body:
            setattr(eq, k, body[k])
            changed = True
    if cover_url:
        eq.cover_img_url = cover_url
        changed = True

    cat = (eq.category or "").strip()
    if cat == "出售" and eq.listing_type != models.Equipment.LISTING_SALE:
        eq.listing_type = models.Equipment.LISTING_SALE
        changed = True
    elif cat == "出租" and eq.listing_type != models.Equipment.LISTING_RENT:
        eq.listing_type = models.Equipment.LISTING_RENT
        changed = True

    if changed:
        # 编辑后需要重新审核（保持规则简单明确）
        if eq.status == models.Equipment.STATUS_ON_SHELF:
            eq.status = models.Equipment.STATUS_PENDING_REVIEW
        eq.save()

    return _json_response(True, data=_equipment_to_dict(eq))


@csrf_exempt
@require_http_methods(["POST"])
def api_my_equipment_off_shelf(request, equipment_id: int):
    user, err = _require_user(request)
    if err:
        return err
    eq = models.Equipment.objects.filter(equipment_id=equipment_id, owner_id=user.id).first()
    if not eq:
        return _json_response(False, message="商品不存在或无权限", status=404)
    if eq.status != models.Equipment.STATUS_ON_SHELF:
        return _json_response(False, message="仅已上架商品可下架", status=400)
    eq.status = models.Equipment.STATUS_OFF
    eq.save(update_fields=["status"])
    return _json_response(True)


@csrf_exempt
@require_http_methods(["DELETE"])
def api_my_equipment_delete(request, equipment_id: int):
    user, err = _require_user(request)
    if err:
        return err
    eq = models.Equipment.objects.filter(equipment_id=equipment_id, owner_id=user.id).first()
    if not eq:
        return _json_response(False, message="商品不存在或无权限", status=404)
    if eq.status in (
        models.Equipment.STATUS_PENDING_DELIVERY,
        models.Equipment.STATUS_PENDING_PICKUP,
        models.Equipment.STATUS_RENTING,
    ):
        return _json_response(False, message="订单进行中，暂不可删除", status=400)
    if eq.status not in (
        models.Equipment.STATUS_OFF,
        models.Equipment.STATUS_SOLD,
        models.Equipment.STATUS_REJECTED,
        models.Equipment.STATUS_WITHDRAWN,
        models.Equipment.STATUS_PENDING_REVIEW,
    ):
        return _json_response(False, message="当前状态不可删除", status=400)
    eq.delete()
    return _json_response(True)


@csrf_exempt
@require_http_methods(["POST"])
def api_my_equipment_on_shelf(request, equipment_id: int):
    user, err = _require_user(request)
    if err:
        return err
    eq = models.Equipment.objects.filter(equipment_id=equipment_id, owner_id=user.id).first()
    if not eq:
        return _json_response(False, message="商品不存在或无权限", status=404)
    if eq.status not in (
        models.Equipment.STATUS_OFF,
        models.Equipment.STATUS_REJECTED,
        models.Equipment.STATUS_WITHDRAWN,
    ):
        return _json_response(False, message="仅已下架/已驳回/已撤回商品可重新申请上架", status=400)
    eq.status = models.Equipment.STATUS_PENDING_REVIEW
    eq.save(update_fields=["status"])
    return _json_response(True)


@csrf_exempt
@require_http_methods(["POST"])
def api_my_equipment_withdraw(request, equipment_id: int):
    """用户撤回「待审核」的上架申请。"""
    user, err = _require_user(request)
    if err:
        return err
    eq = models.Equipment.objects.filter(equipment_id=equipment_id, owner_id=user.id).first()
    if not eq:
        return _json_response(False, message="商品不存在或无权限", status=404)
    if eq.status != models.Equipment.STATUS_PENDING_REVIEW:
        return _json_response(False, message="仅「待审核」商品可撤回申请", status=400)
    eq.status = models.Equipment.STATUS_WITHDRAWN
    eq.save(update_fields=["status"])
    return _json_response(True)

