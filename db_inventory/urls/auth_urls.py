from django.urls import path, include
from db_inventory.views import *
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)


urlpatterns = [
    # audfit logs
    path("audit-logs/", audit_log_list, name="audit-log-list"),
    path("audit-logs/<str:public_id>/", audit_log_detail, name="audit-log-detail"),

    # User Sessions ---
    path('sessions/revoke-all/', user_session_revoke_all_view, name='user-session-revoke-all'),

    # Lock/Unlock User Accounts
    path('users/<str:public_id>/lock/', user_lock_view, name='user-lock'),
    path('users/<str:public_id>/unlock/', user_unlock_view, name='user-unlock'),

    # Admin triggers a password reset (temp password + optional email)
    path(
        'users/<str:user_public_id>/reset-password/',
        admin_reset_user_password_view,
        name='admin-reset-user-password'
    ),
    # rename site
    path('site/rename/', site_rename_view, name='site-rename'),

    path("site-name-changes/", site_name_chnage_list),
    path("site-name-changes/<int:pk>/", site_name_chnage_detail),
    # relocate site
    path('site/relocate/', site_relocate_view, name='site-relocate'),
    # update user demographics
    path('users/<str:public_id>/update-profile/', admin_update_user_demographics, name='admin-update-user-profile')


]