# db_inventory/api/admin_urls.py
from django.urls import path

from db_inventory.viewsets import asset_returns_viewset

urlpatterns = [

    # -------------------------
    # Item workflow (specific first)
    # -------------------------

    path( "returns/items/<str:public_id>/approve/", asset_returns_viewset.AdminReturnRequestItemWorkflowViewSet.as_view({"post": "approve"}), name="admin-return-item-approve", ),
    path( "returns/items/<str:public_id>/deny/", asset_returns_viewset.AdminReturnRequestItemWorkflowViewSet.as_view({"post": "deny"}), name="admin-return-item-deny", ),
    # -------------------------
    # Return Requests (Admin)
    # -------------------------

    path( "returns/", asset_returns_viewset.AdminReturnRequestViewSet.as_view({"get": "list"}), name="admin-return-request-list", ),

    path( "returns/pending/", asset_returns_viewset.AdminReturnRequestViewSet.as_view({"get": "pending"}), name="admin-return-request-pending", ),

    # Request workflow
    path( "returns/<str:public_id>/approve/",  asset_returns_viewset.AdminReturnRequestWorkflowViewSet.as_view({"post": "approve"}),  name="admin-return-request-approve", ),
    path( "returns/<str:public_id>/deny/", asset_returns_viewset.AdminReturnRequestWorkflowViewSet.as_view({"post": "deny"}), name="admin-return-request-deny", ),

    path( "returns/<str:public_id>/resolve/", asset_returns_viewset.AdminReturnRequestWorkflowViewSet.as_view({"post": "resolve"}), name="admin-return-request-resolve", ),

    path( "returns/<str:public_id>/", asset_returns_viewset.AdminReturnRequestViewSet.as_view({"get": "retrieve"}), name="admin-return-request-detail", ),
]