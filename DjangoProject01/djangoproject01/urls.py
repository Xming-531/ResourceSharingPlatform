"""
URL configuration for djangoproject01 project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path
from users import views
from users.apis import router as api

urlpatterns = [
    path("admin/", admin.site.urls),
    # ---- SPA JSON APIs for Vue + axios ----
    path("api/auth/register", api.api_register),
    path("api/auth/login", api.api_login),
    path("api/auth/logout", api.api_logout),
    path("api/public/admin-support-phone", api.api_public_admin_support_phone),
    path("api/me", api.api_me),
    path("api/me/phone", api.api_me_phone),
    path("api/me/password", api.api_me_password),
    path("api/me/avatar", api.api_me_avatar),
    path("api/me/identity-verify", api.api_me_identity_verify),
    path("api/me/account", api.api_me_delete_account),
    # public index list (only 已上架)
    path("api/home/marquee", api.api_home_marquee),
    path("api/equipments", api.api_equipments_public),
    path("api/equipments/<int:equipment_id>/view", api.api_equipment_view),
    # user create (待审核)
    path("api/equipments/create", api.api_equipment_create),
    path("api/my/equipments", api.api_my_equipments),
    path("api/my/equipments/<int:equipment_id>", api.api_my_equipment_update),
    path(
        "api/my/equipments/<int:equipment_id>/off_shelf", api.api_my_equipment_off_shelf
    ),
    path("api/my/equipments/<int:equipment_id>/delete", api.api_my_equipment_delete),
    path(
        "api/my/equipments/<int:equipment_id>/on_shelf", api.api_my_equipment_on_shelf
    ),
    path(
        "api/my/equipments/<int:equipment_id>/withdraw", api.api_my_equipment_withdraw
    ),
    path("api/my/favorites", api.api_my_favorites),
    path("api/my/favorites/add", api.api_favorite_add),
    path("api/my/favorites/<int:equipment_id>", api.api_favorite_remove),
    path("api/admin/users", api.api_admin_users),
    path("api/admin/users/<int:user_id>/disable", api.api_admin_user_disable),
    path(
        "api/admin/users/<int:user_id>/reset-password",
        api.api_admin_user_reset_password,
    ),
    path("api/admin/users/<int:user_id>", api.api_admin_user_delete),
    path("api/admin/me", api.api_admin_me_delete),
    path("api/admin/dashboard-stats", api.api_admin_dashboard_stats),
    path("api/admin/home-marquee", api.api_admin_home_marquee),
    path("api/admin/home-marquee/<int:slide_id>", api.api_admin_home_marquee_item),
    path("api/admin/equipments", api.api_admin_equipments),
    path(
        "api/admin/equipments/<int:equipment_id>/approve",
        api.api_admin_equipment_approve,
    ),
    path(
        "api/admin/equipments/<int:equipment_id>/reject",
        api.api_admin_equipment_reject,
    ),
    path(
        "api/admin/equipments/<int:equipment_id>/off_shelf",
        api.api_admin_equipment_off_shelf,
    ),
    path(
        "api/admin/equipments/<int:equipment_id>/delete", api.api_admin_equipment_delete
    ),
    path("api/admin/orders", api.api_admin_orders),
    path("api/admin/orders/<int:order_id>/delete", api.api_admin_order_delete),
    path("api/admin/orders/<int:order_id>", api.api_admin_order_detail),
    path("api/admin/works", api.api_admin_works),
    path("api/admin/works/<int:work_id>/approve", api.api_admin_work_approve),
    path("api/admin/works/<int:work_id>/reject", api.api_admin_work_reject),
    path("api/admin/works/<int:work_id>/off_shelf", api.api_admin_work_off_shelf),
    path("api/admin/works/<int:work_id>/on_shelf", api.api_admin_work_on_shelf),
    path("api/admin/works/<int:work_id>/delete", api.api_admin_work_delete),
    path("api/orders/checkout", api.api_order_checkout),
    path("api/orders/<int:order_id>/delete", api.api_order_delete),
    path("api/orders/<int:order_id>", api.api_order_detail),
    path(
        "api/orders/<int:order_id>/confirm-handover-owner",
        api.api_order_confirm_handover_owner,
    ),
    path(
        "api/orders/<int:order_id>/confirm-handover-buyer",
        api.api_order_confirm_handover_buyer,
    ),
    path(
        "api/orders/<int:order_id>/confirm-return-owner",
        api.api_order_confirm_return_owner,
    ),
    path(
        "api/orders/<int:order_id>/confirm-return-buyer",
        api.api_order_confirm_return_buyer,
    ),
    path("api/orders/<int:order_id>/early-return", api.api_order_early_return),
    path(
        "api/orders/<int:order_id>/early-return-owner", api.api_order_early_return_owner
    ),
    path(
        "api/orders/<int:order_id>/early-return-owner-reject",
        api.api_order_early_return_owner_reject,
    ),
    path(
        "api/orders/<int:order_id>/request-normal-return",
        api.api_order_request_normal_return,
    ),
    path(
        "api/orders/<int:order_id>/confirm-normal-return-owner",
        api.api_order_confirm_normal_return_owner,
    ),
    path(
        "api/orders/<int:order_id>/request-overdue-return",
        api.api_order_request_overdue_return,
    ),
    path("api/my/orders", api.api_my_orders),
    path("api/my/sales-orders", api.api_my_sales_orders),
    path("api/my/billing-messages", api.api_my_billing_messages),
    path(
        "api/my/billing-messages/<int:message_id>/delete",
        api.api_my_billing_message_delete,
    ),
    path("api/works", api.api_works_public),
    path(
        "api/works/<int:work_id>/comments/<int:comment_id>", api.api_work_comment_delete
    ),
    path("api/works/<int:work_id>/comments", api.api_work_comments),
    path("api/admin/work-comments", api.api_admin_work_comments),
    path(
        "api/admin/work-comments/<int:comment_id>/approve",
        api.api_admin_work_comment_approve,
    ),
    path(
        "api/admin/work-comments/<int:comment_id>/reject",
        api.api_admin_work_comment_reject,
    ),
    path("api/admin/work-comments/<int:comment_id>", api.api_admin_work_comment_delete),
    path("api/my/work-comments", api.api_my_work_comments),
    path("api/my/works", api.api_my_works),
    path("api/my/works/create", api.api_work_create),
    path("api/my/works/<int:work_id>/reapply", api.api_my_work_reapply),
    path("api/my/works/<int:work_id>/withdraw", api.api_my_work_withdraw),
    path("api/my/works/<int:work_id>/off_shelf", api.api_my_work_off_shelf),
    path("api/my/works/<int:work_id>/delete", api.api_my_work_delete),
    path("api/my/works/<int:work_id>", api.api_my_work_item),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
