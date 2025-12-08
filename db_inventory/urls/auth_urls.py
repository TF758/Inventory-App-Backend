from django.urls import path, include
from db_inventory.views import *
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)


urlpatterns = [
    # User Sessions ---
    path('sessions/revoke-all/', user_session_revoke_all_view, name='user-session-revoke-all'),

    # Lock/Unlock User Accounts
    path('users/<str:public_id>/lock/', user_lock_view, name='user-lock'),
    path('users/<str:public_id>/unlock/', user_unlock_view, name='user-unlock'),

    # Admin triggers a password reset (temp password + optional email)
    path(
        'ausers/<str:user_public_id>/reset-password/',
        admin_reset_user_password_view,
        name='admin-reset-user-password'
    ),
    path ('logs/',admin_logs, name='user-log-records' )


]