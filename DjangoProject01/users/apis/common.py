import json
import math
import os
from datetime import date, datetime, timedelta, timezone as dt_timezone
from decimal import ROUND_HALF_UP, Decimal
from io import BytesIO
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.hashers import check_password
from django.db import transaction
from django.db.models import Count, DateTimeField, F, Q, Sum
from django.db.models.functions import Coalesce, TruncDate
from django.http import HttpRequest, JsonResponse
from django.http.multipartparser import MultiPartParser, MultiPartParserError
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from users import models


# ---------- small helpers ----------


def _datetime_to_iso(dt: Optional[datetime]) -> Optional[str]:
    """输出带时区偏移的 ISO 时间，避免前端把无时区字符串当成本地时间而偏差 8 小时。"""
    if dt is None:
        return None
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, dt_timezone.utc)
    return dt.isoformat()


def _json_response(
    ok: bool, data: Any = None, message: str = "", status: int = 200
) -> JsonResponse:
    return JsonResponse(
        {"ok": ok, "message": message, "data": data},
        status=status,
        json_dumps_params={"ensure_ascii": False},
    )


def _get_json_body(request: HttpRequest) -> Dict[str, Any]:
    if not request.body:
        return {}
    try:
        return json.loads(request.body.decode("utf-8"))
    except Exception:
        return {}


def _parse_multipart(
    request: HttpRequest,
) -> Tuple[Dict[str, Any], Any, Optional[JsonResponse]]:
    """
    Django does not automatically parse multipart bodies for PATCH/PUT.
    This helper parses multipart for any method and returns (data, files, error_response).
    """
    try:
        parser = MultiPartParser(
            request.META,
            BytesIO(request.body or b""),
            request.upload_handlers,
            request.encoding or "utf-8",
        )
        post, files = parser.parse()
        data = {k: post.get(k) for k in post.keys()}
        return data, files, None
    except MultiPartParserError:
        return {}, None, _json_response(False, message="multipart 解析失败", status=400)


def _multipart_post_or_parse(
    request: HttpRequest,
) -> Tuple[Dict[str, Any], Any, Optional[JsonResponse]]:
    """
    POST multipart: use Django's POST/FILES so the body is streamed (large uploads OK).
    PATCH/PUT: use _parse_multipart (reads request.body; keep DATA_UPLOAD_MAX_MEMORY_SIZE high enough).
    """
    ct = request.content_type or ""
    if request.method == "POST" and ct.startswith("multipart/form-data"):
        try:
            post = request.POST
            files = request.FILES
        except MultiPartParserError:
            return {}, None, _json_response(False, message="multipart 解析失败", status=400)
        data = {k: post.get(k) for k in post.keys()}
        return data, files, None
    return _parse_multipart(request)


def _parse_auth_header(request: HttpRequest) -> Optional[str]:
    raw = request.headers.get("Authorization") or ""
    raw = raw.strip()
    if not raw:
        return None
    parts = raw.split()
    if len(parts) == 1:
        return parts[0]
    if len(parts) >= 2 and parts[0].lower() in ("bearer", "token"):
        return parts[1]
    return None


def _get_user_by_token(request: HttpRequest) -> Optional[models.User]:
    token = _parse_auth_header(request)
    if not token:
        return None
    try:
        t = models.AuthToken.objects.select_related("user").get(key=token)
    except models.AuthToken.DoesNotExist:
        return None
    return t.user


def _require_user(
    request: HttpRequest,
) -> Tuple[Optional[models.User], Optional[JsonResponse]]:
    user = _get_user_by_token(request)
    if not user:
        return None, _json_response(False, message="未登录", status=401)
    if getattr(user, "status", 1) != 1:
        return None, _json_response(False, message="账号已被禁用", status=403)
    return user, None


def _resolve_user(
    request: HttpRequest,
) -> Tuple[Optional[models.User], Optional[JsonResponse]]:
    """Token（SPA）或 Django 会话登录（模板页）均可。"""
    user = _get_user_by_token(request)
    if user:
        if getattr(user, "status", 1) != 1:
            return None, _json_response(False, message="账号已被禁用", status=403)
        return user, None
    u = getattr(request, "user", None)
    if u is not None and u.is_authenticated and isinstance(u, models.User):
        if getattr(u, "status", 1) != 1:
            return None, _json_response(False, message="账号已被禁用", status=403)
        return u, None
    return None, _json_response(False, message="未登录", status=401)


def _is_admin(user: models.User) -> bool:
    # You can standardize your role values later; this keeps compatibility.
    return str(user.role).lower() in ("0", "admin", "管理员") or bool(
        getattr(user, "is_superuser", False)
    )


def _require_admin(
    request: HttpRequest,
) -> Tuple[Optional[models.User], Optional[JsonResponse]]:
    user, err = _require_user(request)
    if err:
        return None, err
    if not _is_admin(user):
        return None, _json_response(False, message="需要管理员权限", status=403)
    return user, None


def _effective_listing_type(eq: models.Equipment) -> str:
    """
    交易类型真源：category 为「出租/出售」时与上架表单一致；否则以 listing_type 字段为准。
    避免旧数据 category=出售 但 listing_type 仍为 rent 时下单走错租赁流程。
    """
    c = (eq.category or "").strip()
    if c == "出售":
        return models.Equipment.LISTING_SALE
    if c == "出租":
        return models.Equipment.LISTING_RENT
    lt = getattr(eq, "listing_type", None) or models.Equipment.LISTING_RENT
    if lt in (models.Equipment.LISTING_RENT, models.Equipment.LISTING_SALE):
        return lt
    return models.Equipment.LISTING_RENT


def _equipment_to_dict(
    eq: models.Equipment,
    include_owner: bool = False,
    *,
    is_favorited: Optional[bool] = None,
) -> Dict[str, Any]:
    d: Dict[str, Any] = {
        "equipment_id": eq.equipment_id,
        "owner_id": eq.owner_id,
        "title": eq.title,
        "category": eq.category,
        "brand": eq.brand,
        "model": eq.model,
        "description": eq.description,
        "listing_type": _effective_listing_type(eq),
        "price": str(eq.price),
        "deposit": str(eq.deposit),
        "cover_img_url": eq.cover_img_url,
        "status": eq.status,
        "location": eq.location,
        "view_count": eq.view_count,
        "created_at": eq.created_at.isoformat() if eq.created_at else None,
    }
    if include_owner:
        owner = models.User.objects.filter(id=eq.owner_id).first()
        d["owner"] = (
            None
            if not owner
            else {"id": owner.id, "username": owner.username, "phone": owner.phone}
        )
    if is_favorited is not None:
        d["is_favorited"] = is_favorited
    return d


def _optional_user(request: HttpRequest) -> Optional[models.User]:
    """已登录则返回用户，未登录不报错（用于公开列表排除自己的商品、标记收藏状态）。"""
    u = _get_user_by_token(request)
    if u is not None and getattr(u, "status", 1) == 1:
        return u
    u2 = getattr(request, "user", None)
    if (
        u2 is not None
        and getattr(u2, "is_authenticated", False)
        and isinstance(u2, models.User)
    ):
        if getattr(u2, "status", 1) == 1:
            return u2
    return None

