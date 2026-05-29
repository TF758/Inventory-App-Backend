from django.urls import path, include


from .viewsets import *

"""
API URL structure:

- CRUD inventory records: /equipments, /accessories, /consumables
- Inventory operations (assign, use, restock, events): /inventory/...
- phsyical site structure: /departments, /locations, /rooms
"""

urlpatterns = [

    # ----------------------------
    # Core Modules
    # ----------------------------
    path("auth/", include("core.urls.auth_urls")),

    path("", include("core.notifications.urls")),

    # ----------------------------
    # Auth / Session
    # ----------------------------
    path("login/", general_viewsets.SessionTokenLoginView.as_view(), name="login"),
    path("logout/", general_viewsets.LogoutAPIView.as_view(), name="logout"),
    path("refresh/", general_viewsets.RefreshAPIView.as_view(), name="session_refresh"),

  


    # ----------------------------
    # Password Reset
    # ----------------------------
    path("password-reset/request/", general_viewsets.PasswordResetRequestView.as_view(), name="password-reset-request"),
    path("password-reset/confirm/", general_viewsets.PasswordResetConfirmView.as_view(), name="password-reset-confirm"),
    path("change-password/", auth_viewsets.ChangePasswordView.as_view(), name="password_change"),
    path("reset-password/validate-token/", general_viewsets.PasswordResetValidateView.as_view(), name="password-reset-validate"),

]