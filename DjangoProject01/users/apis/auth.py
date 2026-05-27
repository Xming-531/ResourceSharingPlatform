import os
from uuid import uuid4

from django.conf import settings
from django.contrib.auth import authenticate
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from users import models
from users.apis.common import _get_json_body, _is_admin, _json_response, _parse_auth_header


# ---------- Auth ----------


@csrf_exempt
@require_http_methods(["POST"])
def api_register(request):
    body = _get_json_body(request)
    username = (body.get("username") or "").strip()
    password = body.get("password") or ""
    phone = (body.get("phone") or "").strip()
    if not username or not password or not phone:
        return _json_response(False, message="缺少参数：username/password/phone", status=400)
    if models.User.objects.filter(username=username).exists():
        return _json_response(False, message="用户名已存在", status=409)
    user = models.User(username=username, phone=phone, role="1", status=1)
    user.set_password(password)
    user.save()
    return _json_response(
        True,
        data={
            "id": user.id,
            "username": user.username,
            "role": user.role,
            "avatar_url": user.avatar_url,
            "identity_verified": bool(getattr(user, "identity_verified", False)),
        },
    )


@csrf_exempt
@require_http_methods(["POST"])
def api_login(request):
    body = _get_json_body(request)
    username = (body.get("username") or "").strip()
    password = body.get("password") or ""
    if not username or not password:
        return _json_response(False, message="缺少参数：username/password", status=400)

    user = authenticate(username=username, password=password)
    if not user:
        return _json_response(False, message="用户名或密码错误", status=401)
    if getattr(user, "status", 1) != 1:
        return _json_response(False, message="账号已被禁用", status=403)

    key = models.AuthToken.new_key()
    models.AuthToken.objects.create(key=key, user=user)
    return _json_response(
        True,
        data={
            "token": key,
            "user": {
                "id": user.id,
                "username": user.username,
                "phone": user.phone,
                "role": user.role,
                "avatar_url": user.avatar_url,
                "identity_verified": bool(getattr(user, "identity_verified", False)),
            },
        },
    )


@csrf_exempt
@require_http_methods(["POST"])
def api_logout(request):
    token = _parse_auth_header(request)
    if token:
        models.AuthToken.objects.filter(key=token).delete()
    return _json_response(True)


@require_http_methods(["GET"])
def api_public_admin_support_phone(request):
    """登录页等公开场景：返回一名启用状态管理员的联系电话（随库中数据变化）。"""
    phone = ""
    for u in models.User.objects.filter(status=1).order_by("-is_superuser", "id"):
        if not _is_admin(u):
            continue
        p = (u.phone or "").strip()
        if p:
            phone = p
            break
    return _json_response(True, data={"phone": phone})

