from django.urls import path, include

from core.viewsets import agreement_viewsets

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


        # ----------------------------
    # Agreements
    # ----------------------------

    path("agreements/", agreement_viewsets.AssetAgreementViewSet.as_view({
        "get": "list",
        "post": "create"
    }), name="agreements"),

    path("agreements/expiring/", agreement_viewsets.AssetAgreementViewSet.as_view({
        "get": "expiring"
    }), name="agreements-expiring"),

    path("agreements/<str:public_id>/assets/", agreement_viewsets.AssetAgreementViewSet.as_view({
        "get": "assets"
    }), name="agreement-assets"),

    path("agreements/<str:public_id>/", agreement_viewsets.AssetAgreementViewSet.as_view({
        "get": "retrieve",
        "put": "update",
        "patch": "partial_update",
        "delete": "destroy"
    }), name="agreement-detail"),


    # ----------------------------
    # Agreement Items
    # ----------------------------

    path("agreement-items/", agreement_viewsets.AssetAgreementItemViewSet.as_view({
        "get": "list",
        "post": "create"
    }), name="agreement-items"),

    path("agreement-items/<int:pk>/", agreement_viewsets.AssetAgreementItemViewSet.as_view({
        "get": "retrieve",
        "put": "update",
        "patch": "partial_update",
        "delete": "destroy"
    }), name="agreement-item-detail"),
]