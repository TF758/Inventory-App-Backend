from django.urls import path, include

from db_inventory.viewsets import audit_viewsets
from db_inventory.viewsets import auth_viewsets

urlpatterns = [
    # --- Audit Logs ---
    path( "audit-logs/", audit_viewsets.AuditLogViewSet.as_view({"get": "list"}), name="audit-log-list", ),
    path( "audit-logs/<str:public_id>/", audit_viewsets.AuditLogViewSet.as_view({"get": "retrieve"}), name="audit-log-detail", ),
    # --- User Sessions ---
    path( "sessions/revoke-all/", auth_viewsets.RevokeUserSessionsViewset.as_view({"post": "revoke_all"}), name="user-session-revoke-all", ),

    # --- Lock / Unlock User Accounts ---
    path( "users/<str:public_id>/lock/", auth_viewsets.UserLockViewSet.as_view({"post": "lock"}), name="user-lock", ),
    path( "users/<str:public_id>/unlock/", auth_viewsets.UserLockViewSet.as_view({"post": "unlock"}), name="user-unlock", ),

    # --- Admin Password Reset ---
    path( "users/<str:user_public_id>/reset-password/", auth_viewsets.AdminResetUserPasswordView.as_view(), name="admin-reset-user-password", ),

    # --- Site Admin ---
    path( "site/rename/", auth_viewsets.SiteNameChangeAPIView.as_view(), name="site-rename", ),
    path( "site/relocate/", auth_viewsets.SiteRelocationAPIView.as_view(), name="site-relocate", ),

    # --- Site Name Change History ---
    path( "site-name-changes/", auth_viewsets.SiteNameChangeListAPIView.as_view(), name="site-name-change-list", ),
    path( "site-name-changes/<int:pk>/", auth_viewsets.SiteNameChangeDetailAPIView.as_view(), name="site-name-change-detail", ),

    # --- Admin User Updates ---
    path( "users/<str:public_id>/update-profile/", auth_viewsets.AdminUpdateUserView.as_view(), name="admin-update-user-profile", ),
]