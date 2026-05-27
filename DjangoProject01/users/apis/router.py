"""
API router module.

Import this as `api` from URL configuration to avoid importing the legacy
monolithic `users/api.py`.
"""

# Auth
from users.apis.auth import api_login, api_logout, api_public_admin_support_phone, api_register

# Me
from users.apis.me import (
    api_me,
    api_me_avatar,
    api_me_delete_account,
    api_me_identity_verify,
    api_me_password,
    api_me_phone,
)

# Home marquee (public + admin)
from users.apis.home import api_admin_home_marquee, api_admin_home_marquee_item, api_home_marquee

# Equipments (public + my)
from users.apis.equipments import (
    api_equipment_create,
    api_equipment_view,
    api_equipments_public,
    api_my_equipment_delete,
    api_my_equipment_off_shelf,
    api_my_equipment_on_shelf,
    api_my_equipment_withdraw,
    api_my_equipment_update,
    api_my_equipments,
)

# Favorites
from users.apis.favorites import api_favorite_add, api_favorite_remove, api_my_favorites

# Works + comments
from users.apis.works import (
    api_admin_work_comment_approve,
    api_admin_work_comment_delete,
    api_admin_work_comment_reject,
    api_admin_work_comments,
    api_admin_work_approve,
    api_admin_work_delete,
    api_admin_work_off_shelf,
    api_admin_work_on_shelf,
    api_admin_work_reject,
    api_admin_works,
    api_my_work_comments,
    api_my_work_delete,
    api_my_work_item,
    api_my_work_off_shelf,
    api_my_work_reapply,
    api_my_work_withdraw,
    api_my_works,
    api_work_comment_delete,
    api_work_comments,
    api_work_create,
    api_works_public,
)

# Orders + billing
from users.apis.orders import (
    api_admin_order_delete,
    api_my_billing_message_delete,
    api_my_billing_messages,
    api_my_orders,
    api_my_sales_orders,
    api_order_checkout,
    api_order_confirm_handover_buyer,
    api_order_confirm_handover_owner,
    api_order_confirm_normal_return_owner,
    api_order_confirm_return_buyer,
    api_order_confirm_return_owner,
    api_order_delete,
    api_order_detail,
    api_order_early_return,
    api_order_early_return_owner,
    api_order_early_return_owner_reject,
    api_order_request_normal_return,
    api_order_request_overdue_return,
)

# Admin (users, equipments, orders list/detail, dashboard)
from users.apis.admin import (
    api_admin_dashboard_stats,
    api_admin_equipment_approve,
    api_admin_equipment_delete,
    api_admin_equipment_off_shelf,
    api_admin_equipment_reject,
    api_admin_equipments,
    api_admin_me_delete,
    api_admin_order_detail,
    api_admin_orders,
    api_admin_user_delete,
    api_admin_user_disable,
    api_admin_user_reset_password,
    api_admin_users,
)

