import os
from typing import Any, Dict, Optional
from uuid import uuid4

from django.conf import settings
from django.db.models import Count, Q
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from users import models
from users.apis.common import (
    _get_json_body,
    _is_admin,
    _json_response,
    _multipart_post_or_parse,
    _optional_user,
    _require_admin,
    _require_user,
    _resolve_user,
)


# ---------- Photo works (square) ----------


def _work_to_dict(w: models.PhotoWork, include_user: bool = False) -> Dict[str, Any]:
    d: Dict[str, Any] = {
        "work_id": w.work_id,
        "user_id": w.user_id,
        "image_url": w.image_url,
        "camera_name": w.camera_name,
        "lens_name": w.lens_name,
        "iso": w.iso,
        "shutter_speed": w.shutter_speed,
        "aperture": w.aperture,
        "shoot_location": w.shoot_location,
        "status": w.status,
        "created_at": w.created_at.isoformat() if w.created_at else None,
    }
    if include_user:
        u = models.User.objects.filter(id=w.user_id).first()
        d["user"] = None if not u else {"id": u.id, "username": u.username, "avatar_url": u.avatar_url}
    return d


@require_http_methods(["GET"])
def api_works_public(request):
    qs = (
        models.PhotoWork.objects.filter(status=models.PhotoWork.STATUS_APPROVED)
        .annotate(
            comment_count=Count(
                "comments",
                filter=Q(comments__status=models.PhotoWorkComment.STATUS_APPROVED),
            )
        )
        .order_by("-created_at")
    )
    data = []
    for w in qs:
        d = _work_to_dict(w, include_user=True)
        d["comment_count"] = int(getattr(w, "comment_count", 0) or 0)
        data.append(d)
    return _json_response(True, data=data)


@require_http_methods(["GET"])
def api_my_works(request):
    user, err = _require_user(request)
    if err:
        return err
    qs = models.PhotoWork.objects.filter(user_id=user.id).order_by("-created_at")
    data = [_work_to_dict(w, include_user=False) for w in qs]
    return _json_response(True, data=data)


@csrf_exempt
@require_http_methods(["POST"])
def api_work_create(request):
    user, err = _require_user(request)
    if err:
        return err
    is_multipart = (request.content_type or "").startswith("multipart/form-data")
    if not is_multipart:
        return _json_response(False, message="请使用 multipart/form-data 上传作品", status=400)
    body, files, parse_err = _multipart_post_or_parse(request)
    if parse_err:
        return parse_err
    if not files or not files.get("image"):
        return _json_response(False, message="缺少图片字段 image", status=400)
    required = ["camera_name", "lens_name", "iso", "shutter_speed", "aperture", "shoot_location"]
    missing = [k for k in required if not (body.get(k) or "").__str__().strip()]
    if missing:
        return _json_response(False, message=f"缺少参数：{','.join(missing)}", status=400)

    f = files["image"]
    ext = os.path.splitext(getattr(f, "name", "") or "")[1].lower()[:10]
    if ext not in (".jpg", ".jpeg", ".png", ".webp", ".gif"):
        return _json_response(False, message="图片仅支持 jpg/jpeg/png/webp/gif", status=400)
    os.makedirs(settings.MEDIA_ROOT, exist_ok=True)
    filename = f"work_{user.id}_{uuid4().hex}{ext}"
    abs_path = os.path.join(str(settings.MEDIA_ROOT), filename)
    with open(abs_path, "wb") as out:
        for chunk in f.chunks():
            out.write(chunk)
    image_url = f"{settings.MEDIA_URL}{filename}"

    w = models.PhotoWork.objects.create(
        user_id=user.id,
        image_url=image_url,
        camera_name=str(body["camera_name"]).strip(),
        lens_name=str(body["lens_name"]).strip(),
        iso=str(body["iso"]).strip(),
        shutter_speed=str(body["shutter_speed"]).strip(),
        aperture=str(body["aperture"]).strip(),
        shoot_location=str(body["shoot_location"]).strip(),
        status=models.PhotoWork.STATUS_PENDING,
    )
    return _json_response(True, data=_work_to_dict(w, include_user=True))


def _work_image_abs_path_from_url(image_url: str) -> Optional[str]:
    """MEDIA_URL 下的文件绝对路径，非法则返回 None。"""
    if not image_url:
        return None
    mu = settings.MEDIA_URL
    if not str(image_url).startswith(mu):
        return None
    rel = str(image_url)[len(mu):].lstrip("/").replace("\\", "/")
    if not rel or ".." in rel:
        return None
    return os.path.join(str(settings.MEDIA_ROOT), rel)


def _safe_remove_work_image_file(image_url: str) -> None:
    p = _work_image_abs_path_from_url(image_url)
    if p and os.path.isfile(p):
        try:
            os.remove(p)
        except OSError:
            pass


@csrf_exempt
def api_my_work_item(request, work_id: int):
    """GET 详情 / PATCH 修改参数（可选更换图片）。"""
    user, err = _require_user(request)
    if err:
        return err
    w = models.PhotoWork.objects.filter(work_id=work_id, user_id=user.id).first()
    if not w:
        return _json_response(False, message="作品不存在或无权限", status=404)
    if request.method == "GET":
        return _json_response(True, data=_work_to_dict(w, include_user=False))
    if request.method == "PATCH":
        return _api_my_work_patch(request, w)
    return _json_response(False, message="Method Not Allowed", status=405)


def _api_my_work_patch(request, w: models.PhotoWork):
    if w.status not in (
        models.PhotoWork.STATUS_PENDING,
        models.PhotoWork.STATUS_REJECTED,
        models.PhotoWork.STATUS_OFF,
    ):
        return _json_response(
            False,
            message="仅「待审核」「已驳回」「已下架」的作品可修改；已上架请先在管理中下架",
            status=400,
        )
    is_multipart = (request.content_type or "").startswith("multipart/form-data")
    if is_multipart:
        body, files, parse_err = _multipart_post_or_parse(request)
        if parse_err:
            return parse_err
    else:
        body = _get_json_body(request)
        files = None

    fields = ["camera_name", "lens_name", "iso", "shutter_speed", "aperture", "shoot_location"]
    for k in fields:
        if k in body and body.get(k) is not None:
            v = str(body.get(k) or "").strip()
            if not v:
                return _json_response(False, message=f"参数 {k} 不能为空", status=400)
            setattr(w, k, v)

    if is_multipart and files and files.get("image"):
        f = files["image"]
        ext = os.path.splitext(getattr(f, "name", "") or "")[1].lower()[:10]
        if ext not in (".jpg", ".jpeg", ".png", ".webp", ".gif"):
            return _json_response(False, message="图片仅支持 jpg/jpeg/png/webp/gif", status=400)
        old_url = w.image_url
        os.makedirs(settings.MEDIA_ROOT, exist_ok=True)
        filename = f"work_{w.user_id}_{uuid4().hex}{ext}"
        abs_path = os.path.join(str(settings.MEDIA_ROOT), filename)
        with open(abs_path, "wb") as out:
            for chunk in f.chunks():
                out.write(chunk)
        w.image_url = f"{settings.MEDIA_URL}{filename}"
        _safe_remove_work_image_file(old_url)

    if w.status in (models.PhotoWork.STATUS_REJECTED, models.PhotoWork.STATUS_OFF):
        w.status = models.PhotoWork.STATUS_PENDING
    w.save()
    return _json_response(True, data=_work_to_dict(w, include_user=False))


@csrf_exempt
@require_http_methods(["POST"])
def api_my_work_reapply(request, work_id: int):
    """已驳回或已下架：再次提交审核（不改参数时可直接点）。"""
    user, err = _require_user(request)
    if err:
        return err
    w = models.PhotoWork.objects.filter(work_id=work_id, user_id=user.id).first()
    if not w:
        return _json_response(False, message="作品不存在或无权限", status=404)
    if w.status not in (
        models.PhotoWork.STATUS_REJECTED,
        models.PhotoWork.STATUS_OFF,
        models.PhotoWork.STATUS_WITHDRAWN,
    ):
        return _json_response(False, message="仅「已驳回」「已下架」或「已撤回」的作品可重新申请审核", status=400)
    w.status = models.PhotoWork.STATUS_PENDING
    w.save(update_fields=["status"])
    return _json_response(True, data=_work_to_dict(w, include_user=False))


@csrf_exempt
@require_http_methods(["POST"])
def api_my_work_withdraw(request, work_id: int):
    """作者撤回待审核作品的申请（待审核 -> 已撤回）。"""
    user, err = _require_user(request)
    if err:
        return err
    w = models.PhotoWork.objects.filter(work_id=work_id, user_id=user.id).first()
    if not w:
        return _json_response(False, message="作品不存在或无权限", status=404)
    if w.status != models.PhotoWork.STATUS_PENDING:
        return _json_response(False, message="仅「待审核」的作品可撤回申请", status=400)
    w.status = models.PhotoWork.STATUS_WITHDRAWN
    w.save(update_fields=["status"])
    return _json_response(True, data=_work_to_dict(w, include_user=False))


@csrf_exempt
@require_http_methods(["POST"])
def api_my_work_off_shelf(request, work_id: int):
    """作者将已上架作品下架，之后可修改或删除。"""
    user, err = _require_user(request)
    if err:
        return err
    w = models.PhotoWork.objects.filter(work_id=work_id, user_id=user.id).first()
    if not w:
        return _json_response(False, message="作品不存在或无权限", status=404)
    if w.status != models.PhotoWork.STATUS_APPROVED:
        return _json_response(False, message="仅「已上架」的作品可下架", status=400)
    w.status = models.PhotoWork.STATUS_OFF
    w.save(update_fields=["status"])
    return _json_response(True, data=_work_to_dict(w, include_user=False))


@csrf_exempt
@require_http_methods(["DELETE"])
def api_my_work_delete(request, work_id: int):
    user, err = _require_user(request)
    if err:
        return err
    w = models.PhotoWork.objects.filter(work_id=work_id, user_id=user.id).first()
    if not w:
        return _json_response(False, message="作品不存在或无权限", status=404)
    if w.status not in (
        models.PhotoWork.STATUS_PENDING,
        models.PhotoWork.STATUS_REJECTED,
        models.PhotoWork.STATUS_OFF,
    ):
        return _json_response(False, message="仅「待审核」「已驳回」「已下架」的作品可删除；已上架请先下架", status=400)
    img = w.image_url
    w.delete()
    _safe_remove_work_image_file(img)
    return _json_response(True)


@require_http_methods(["GET"])
def api_admin_works(request):
    _, err = _require_admin(request)
    if err:
        return err
    status = (request.GET.get("status") or "").strip()
    qs = models.PhotoWork.objects.all().order_by("-created_at")
    if status:
        qs = qs.filter(status=status)
    data = [_work_to_dict(w, include_user=True) for w in qs]
    return _json_response(True, data=data)


@csrf_exempt
@require_http_methods(["POST"])
def api_admin_work_approve(request, work_id: int):
    _, err = _require_admin(request)
    if err:
        return err
    w = models.PhotoWork.objects.filter(work_id=work_id).first()
    if not w:
        return _json_response(False, message="作品不存在", status=404)
    if w.status not in (models.PhotoWork.STATUS_PENDING, models.PhotoWork.STATUS_REJECTED):
        return _json_response(False, message="仅「待审核」或「已驳回」的作品可通过审核上架", status=400)
    w.status = models.PhotoWork.STATUS_APPROVED
    w.save(update_fields=["status"])
    return _json_response(True, data=_work_to_dict(w, include_user=True))


@csrf_exempt
@require_http_methods(["POST"])
def api_admin_work_reject(request, work_id: int):
    """待审核作品审核不通过，不进入照片展示（与「已下架」区分：下架针对曾上架作品）。"""
    _, err = _require_admin(request)
    if err:
        return err
    w = models.PhotoWork.objects.filter(work_id=work_id).first()
    if not w:
        return _json_response(False, message="作品不存在", status=404)
    if w.status != models.PhotoWork.STATUS_PENDING:
        return _json_response(False, message="仅「待审核」的作品可驳回", status=400)
    w.status = models.PhotoWork.STATUS_REJECTED
    w.save(update_fields=["status"])
    return _json_response(True, data=_work_to_dict(w, include_user=True))


@csrf_exempt
@require_http_methods(["POST"])
def api_admin_work_off_shelf(request, work_id: int):
    _, err = _require_admin(request)
    if err:
        return err
    w = models.PhotoWork.objects.filter(work_id=work_id).first()
    if not w:
        return _json_response(False, message="作品不存在", status=404)
    if w.status != models.PhotoWork.STATUS_APPROVED:
        return _json_response(False, message="仅「已上架」的作品可下架", status=400)
    w.status = models.PhotoWork.STATUS_OFF
    w.save(update_fields=["status"])
    return _json_response(True, data=_work_to_dict(w, include_user=True))


@csrf_exempt
@require_http_methods(["POST"])
def api_admin_work_on_shelf(request, work_id: int):
    """管理员将已下架作品重新上架到照片展示（与作者端「重新申请」无关，直接恢复公开展示）。"""
    _, err = _require_admin(request)
    if err:
        return err
    w = models.PhotoWork.objects.filter(work_id=work_id).first()
    if not w:
        return _json_response(False, message="作品不存在", status=404)
    if w.status != models.PhotoWork.STATUS_OFF:
        return _json_response(False, message="仅「已下架」的作品可重新上架", status=400)
    w.status = models.PhotoWork.STATUS_APPROVED
    w.save(update_fields=["status"])
    return _json_response(True, data=_work_to_dict(w, include_user=True))


@csrf_exempt
@require_http_methods(["DELETE", "POST"])
def api_admin_work_delete(request, work_id: int):
    """删除作品：支持 DELETE 或 POST（与审核/下架等管理接口一致，避免部分环境拦截 DELETE）。"""
    _, err = _require_admin(request)
    if err:
        return err
    w = models.PhotoWork.objects.filter(work_id=work_id).first()
    if not w:
        return _json_response(False, message="作品不存在", status=404)
    if w.status not in (models.PhotoWork.STATUS_PENDING, models.PhotoWork.STATUS_OFF, models.PhotoWork.STATUS_REJECTED):
        return _json_response(False, message="仅「待审核」「已下架」或「已驳回」的作品可直接删除；已上架请先下架", status=400)
    img = w.image_url
    w.delete()
    _safe_remove_work_image_file(img)
    return _json_response(True)


def _work_comment_to_dict(c: models.PhotoWorkComment, *, include_user: bool = True) -> Dict[str, Any]:
    d: Dict[str, Any] = {
        "comment_id": c.comment_id,
        "work_id": c.photo_work_id,
        "user_id": c.user_id,
        "content": c.content,
        "status": c.status,
        "created_at": c.created_at.isoformat() if c.created_at else None,
    }
    if include_user:
        u = models.User.objects.filter(id=c.user_id).first()
        d["user"] = None if not u else {"id": u.id, "username": u.username, "avatar_url": u.avatar_url}
    return d


@require_http_methods(["GET"])
def api_my_work_comments(request):
    """当前用户在照片展示下发表过的评论（含关联作品摘要，用于用户端评论管理）。"""
    user, err = _require_user(request)
    if err:
        return err
    uid = int(user.pk)
    qs = list(
        models.PhotoWorkComment.objects.filter(user_id=uid)
        .select_related("photo_work")
        .order_by("-created_at")[:500]
    )
    data = []
    for c in qs:
        row = _work_comment_to_dict(c, include_user=False)
        pw = c.photo_work
        if pw:
            row["work"] = {
                "work_id": pw.work_id,
                "image_url": pw.image_url,
                "shoot_location": pw.shoot_location,
                "status": pw.status,
            }
        else:
            row["work"] = None
        data.append(row)
    return _json_response(True, data=data)


@csrf_exempt
def api_work_comments(request, work_id: int):
    if request.method == "GET":
        w = models.PhotoWork.objects.filter(work_id=work_id, status=models.PhotoWork.STATUS_APPROVED).first()
        if not w:
            return _json_response(False, message="作品不存在或未公开展示", status=404)
        me = _optional_user(request)
        if me:
            qs = w.comments.filter(
                Q(status=models.PhotoWorkComment.STATUS_APPROVED) | Q(user_id=me.id)
            ).order_by("-created_at")[:300]
        else:
            qs = w.comments.filter(status=models.PhotoWorkComment.STATUS_APPROVED).order_by("-created_at")[:300]
        data = [_work_comment_to_dict(c) for c in qs]
        return _json_response(True, data=data)
    if request.method == "POST":
        user, err = _require_user(request)
        if err:
            return err
        w = models.PhotoWork.objects.filter(work_id=work_id, status=models.PhotoWork.STATUS_APPROVED).first()
        if not w:
            return _json_response(False, message="作品不存在或未公开展示", status=404)
        body = _get_json_body(request)
        content = (body.get("content") or "").strip()
        if not content:
            return _json_response(False, message="评论内容不能为空", status=400)
        if len(content) > 2000:
            return _json_response(False, message="评论内容过长", status=400)
        c = models.PhotoWorkComment.objects.create(
            photo_work=w,
            user_id=user.id,
            content=content,
            status=models.PhotoWorkComment.STATUS_PENDING,
        )
        return _json_response(True, data=_work_comment_to_dict(c))
    return _json_response(False, message="Method Not Allowed", status=405)


@csrf_exempt
@require_http_methods(["DELETE"])
def api_work_comment_delete(request, work_id: int, comment_id: int):
    user, err = _resolve_user(request)
    if err:
        return err
    c = models.PhotoWorkComment.objects.filter(comment_id=comment_id, photo_work_id=work_id).first()
    if not c:
        return _json_response(False, message="评论不存在", status=404)
    if c.user_id == user.id:
        c.delete()
        return _json_response(True)
    if _is_admin(user):
        c.delete()
        return _json_response(True)
    return _json_response(False, message="只能删除自己的评论", status=403)


@require_http_methods(["GET"])
def api_admin_work_comments(request):
    _, err = _require_admin(request)
    if err:
        return err
    work_id = (request.GET.get("work_id") or "").strip()
    status = (request.GET.get("status") or "").strip()
    qs = models.PhotoWorkComment.objects.select_related("photo_work").order_by("-created_at")
    if work_id.isdigit():
        qs = qs.filter(photo_work_id=int(work_id))
    if status:
        qs = qs.filter(status=status)
    data = []
    for c in qs[:500]:
        row = _work_comment_to_dict(c)
        pw = c.photo_work
        if pw:
            row["work_shoot_location"] = pw.shoot_location
            row["work_author_id"] = pw.user_id
            row["work"] = _work_to_dict(pw, include_user=True)
        else:
            row["work_shoot_location"] = ""
            row["work_author_id"] = None
            row["work"] = None
        data.append(row)
    return _json_response(True, data=data)


@csrf_exempt
@require_http_methods(["POST"])
def api_admin_work_comment_approve(request, comment_id: int):
    _, err = _require_admin(request)
    if err:
        return err
    c = models.PhotoWorkComment.objects.filter(comment_id=comment_id).first()
    if not c:
        return _json_response(False, message="评论不存在", status=404)
    if c.status not in (models.PhotoWorkComment.STATUS_PENDING, models.PhotoWorkComment.STATUS_REJECTED):
        return _json_response(False, message="仅「待审核」或「已驳回」的评论可通过审核", status=400)
    c.status = models.PhotoWorkComment.STATUS_APPROVED
    c.save(update_fields=["status"])
    return _json_response(True, data=_work_comment_to_dict(c))


@csrf_exempt
@require_http_methods(["POST"])
def api_admin_work_comment_reject(request, comment_id: int):
    _, err = _require_admin(request)
    if err:
        return err
    c = models.PhotoWorkComment.objects.filter(comment_id=comment_id).first()
    if not c:
        return _json_response(False, message="评论不存在", status=404)
    if c.status not in (models.PhotoWorkComment.STATUS_PENDING, models.PhotoWorkComment.STATUS_APPROVED):
        return _json_response(False, message="仅「待审核」或「已通过」的评论可驳回", status=400)
    c.status = models.PhotoWorkComment.STATUS_REJECTED
    c.save(update_fields=["status"])
    return _json_response(True, data=_work_comment_to_dict(c))


@csrf_exempt
@require_http_methods(["DELETE"])
def api_admin_work_comment_delete(request, comment_id: int):
    _, err = _require_admin(request)
    if err:
        return err
    c = models.PhotoWorkComment.objects.filter(comment_id=comment_id).first()
    if not c:
        return _json_response(False, message="评论不存在", status=404)
    c.delete()
    return _json_response(True)

