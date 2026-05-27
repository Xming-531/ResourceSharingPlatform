from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from users import models
from users.apis.common import _equipment_to_dict, _get_json_body, _json_response, _require_user


# ---------- Favorites ----------


@require_http_methods(["GET"])
def api_my_favorites(request):
    user, err = _require_user(request)
    if err:
        return err
    ids = list(
        models.Favorite.objects.filter(user_id=user.id)
        .order_by("-created_at")
        .values_list("equipment_id", flat=True)
    )
    eqs = list(models.Equipment.objects.filter(equipment_id__in=ids))
    eq_map = {e.equipment_id: e for e in eqs}
    data = []
    for eid in ids:
        eq = eq_map.get(eid)
        if not eq:
            continue
        data.append(_equipment_to_dict(eq))
    return _json_response(True, data=data)


@csrf_exempt
@require_http_methods(["POST"])
def api_favorite_add(request):
    user, err = _require_user(request)
    if err:
        return err
    body = _get_json_body(request)
    try:
        equipment_id = int(body.get("equipment_id"))
    except (TypeError, ValueError):
        return _json_response(False, message="equipment_id 无效", status=400)

    eq = models.Equipment.objects.filter(equipment_id=equipment_id).first()
    if not eq:
        return _json_response(False, message="商品不存在", status=404)

    obj, created = models.Favorite.objects.get_or_create(
        user_id=user.id, equipment_id=equipment_id
    )
    return _json_response(
        True,
        data={"equipment_id": equipment_id, "favorited": True, "created": bool(created)},
    )


@csrf_exempt
@require_http_methods(["DELETE"])
def api_favorite_remove(request, equipment_id: int):
    user, err = _require_user(request)
    if err:
        return err
    models.Favorite.objects.filter(user_id=user.id, equipment_id=equipment_id).delete()
    return _json_response(True, data={"equipment_id": equipment_id, "favorited": False})

