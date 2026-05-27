import os
from typing import Any, Dict, Optional, Tuple
from uuid import uuid4

from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from users import models
from users.apis.common import _json_response, _multipart_post_or_parse, _require_admin


def _home_marquee_slide_to_dict(s: models.HomeMarqueeSlide) -> Dict[str, Any]:
    return {
        "id": s.slide_id,
        "image_url": s.image_url,
        "title": s.title,
        "subtitle": s.subtitle or "",
        "track": s.track,
        "sort_order": s.sort_order,
    }


def _home_marquee_slide_admin_dict(s: models.HomeMarqueeSlide) -> Dict[str, Any]:
    d = _home_marquee_slide_to_dict(s)
    d["enabled"] = bool(s.enabled)
    return d


def _parse_bool_loose(v: Any, default: bool = True) -> bool:
    if isinstance(v, bool):
        return v
    if v is None:
        return default
    s = str(v).strip().lower()
    if s in ("0", "false", "no", "off", ""):
        return False
    if s in ("1", "true", "yes", "on"):
        return True
    return default


def _marquee_save_uploaded_image(
    files: Any,
) -> Tuple[Optional[str], Optional[Any]]:
    if not files or not files.get("image"):
        return None, None
    f = files["image"]
    ext = os.path.splitext(getattr(f, "name", "") or "")[1].lower()[:10]
    if ext not in (".jpg", ".jpeg", ".png", ".webp", ".gif"):
        return None, _json_response(False, message="图片仅支持 jpg/jpeg/png/webp/gif", status=400)
    os.makedirs(settings.MEDIA_ROOT, exist_ok=True)
    filename = f"marquee_{uuid4().hex}{ext}"
    abs_path = os.path.join(str(settings.MEDIA_ROOT), filename)
    with open(abs_path, "wb") as out:
        for chunk in f.chunks():
            out.write(chunk)
    url = f"{settings.MEDIA_URL}{filename}"
    return url, None


def api_admin_home_marquee_list(request):
    _, err = _require_admin(request)
    if err:
        return err
    qs = models.HomeMarqueeSlide.objects.all().order_by("track", "sort_order", "slide_id")
    return _json_response(True, data=[_home_marquee_slide_admin_dict(s) for s in qs])


@csrf_exempt
def api_admin_home_marquee(request):
    if request.method == "GET":
        return api_admin_home_marquee_list(request)
    if request.method == "POST":
        return api_admin_home_marquee_create(request)
    return _json_response(False, message="Method Not Allowed", status=405)


def api_admin_home_marquee_create(request):
    _, err = _require_admin(request)
    if err:
        return err
    ct = (request.content_type or "").lower()
    image_url = ""
    title = ""
    subtitle = ""
    track = models.HomeMarqueeSlide.TRACK_FAST
    sort_order = 0
    enabled = True

    if ct.startswith("multipart/form-data"):
        body, files, parse_err = _multipart_post_or_parse(request)
        if parse_err:
            return parse_err
        title = (body.get("title") or "").strip()
        subtitle = (body.get("subtitle") or "").strip()
        try:
            track = int(body.get("track") or models.HomeMarqueeSlide.TRACK_FAST)
        except (TypeError, ValueError):
            track = models.HomeMarqueeSlide.TRACK_FAST
        try:
            sort_order = int(body.get("sort_order") or 0)
        except (TypeError, ValueError):
            sort_order = 0
        enabled = _parse_bool_loose(body.get("enabled"), True)
        url_part, img_err = _marquee_save_uploaded_image(files)
        if img_err:
            return img_err
        image_url = url_part or ""
    else:
        from users.apis.common import _get_json_body

        body = _get_json_body(request)
        title = (body.get("title") or "").strip()
        subtitle = (body.get("subtitle") or "").strip()
        image_url = (body.get("image_url") or "").strip()
        try:
            track = int(body.get("track") or models.HomeMarqueeSlide.TRACK_FAST)
        except (TypeError, ValueError):
            track = models.HomeMarqueeSlide.TRACK_FAST
        try:
            sort_order = int(body.get("sort_order") or 0)
        except (TypeError, ValueError):
            sort_order = 0
        enabled = _parse_bool_loose(body.get("enabled"), True)

    if not title:
        return _json_response(False, message="请填写主标题", status=400)
    if not image_url:
        return _json_response(False, message="请上传图片或填写图片地址 image_url", status=400)
    if track not in (models.HomeMarqueeSlide.TRACK_FAST, models.HomeMarqueeSlide.TRACK_SLOW):
        track = models.HomeMarqueeSlide.TRACK_FAST

    s = models.HomeMarqueeSlide.objects.create(
        image_url=image_url,
        title=title[:120],
        subtitle=subtitle[:200],
        track=track,
        sort_order=max(0, sort_order),
        enabled=enabled,
    )
    return _json_response(True, data=_home_marquee_slide_admin_dict(s))


@csrf_exempt
def api_admin_home_marquee_item(request, slide_id: int):
    if request.method not in ("PATCH", "DELETE"):
        return _json_response(False, message="Method Not Allowed", status=405)
    _, err = _require_admin(request)
    if err:
        return err
    s = models.HomeMarqueeSlide.objects.filter(slide_id=slide_id).first()
    if not s:
        return _json_response(False, message="条目不存在", status=404)

    if request.method == "DELETE":
        s.delete()
        return _json_response(True)

    if request.method != "PATCH":
        return _json_response(False, message="Method Not Allowed", status=405)

    ct = (request.content_type or "").lower()
    if ct.startswith("multipart/form-data"):
        body, files, parse_err = _multipart_post_or_parse(request)
        if parse_err:
            return parse_err
        if "title" in body:
            t = (body.get("title") or "").strip()
            if t:
                s.title = t[:120]
        if "subtitle" in body:
            s.subtitle = (body.get("subtitle") or "").strip()[:200]
        if body.get("track") is not None and str(body.get("track")).strip() != "":
            try:
                tr = int(body.get("track"))
                if tr in (models.HomeMarqueeSlide.TRACK_FAST, models.HomeMarqueeSlide.TRACK_SLOW):
                    s.track = tr
            except (TypeError, ValueError):
                pass
        if body.get("sort_order") is not None and str(body.get("sort_order")).strip() != "":
            try:
                s.sort_order = max(0, int(body.get("sort_order")))
            except (TypeError, ValueError):
                pass
        if body.get("enabled") is not None:
            s.enabled = _parse_bool_loose(body.get("enabled"), s.enabled)
        url_part, img_err = _marquee_save_uploaded_image(files)
        if img_err:
            return img_err
        if url_part:
            s.image_url = url_part
    else:
        from users.apis.common import _get_json_body

        body = _get_json_body(request)
        if "title" in body:
            t = (body.get("title") or "").strip()
            if t:
                s.title = t[:120]
        if "subtitle" in body:
            s.subtitle = (body.get("subtitle") or "").strip()[:200]
        if body.get("track") is not None and str(body.get("track")).strip() != "":
            try:
                tr = int(body.get("track"))
                if tr in (models.HomeMarqueeSlide.TRACK_FAST, models.HomeMarqueeSlide.TRACK_SLOW):
                    s.track = tr
            except (TypeError, ValueError):
                pass
        if body.get("sort_order") is not None and str(body.get("sort_order")).strip() != "":
            try:
                s.sort_order = max(0, int(body.get("sort_order")))
            except (TypeError, ValueError):
                pass
        if body.get("enabled") is not None:
            s.enabled = _parse_bool_loose(body.get("enabled"), s.enabled)
        if body.get("image_url") is not None:
            url = (body.get("image_url") or "").strip()
            if url:
                s.image_url = url

    s.save()
    return _json_response(True, data=_home_marquee_slide_admin_dict(s))


@require_http_methods(["GET"])
def api_home_marquee(request):
    qs = models.HomeMarqueeSlide.objects.filter(enabled=True).order_by(
        "track", "sort_order", "slide_id"
    )
    track1 = []
    track2 = []
    for s in qs:
        d = _home_marquee_slide_to_dict(s)
        if int(s.track) == models.HomeMarqueeSlide.TRACK_SLOW:
            track2.append(d)
        else:
            track1.append(d)
    return _json_response(True, data={"track1": track1, "track2": track2})

