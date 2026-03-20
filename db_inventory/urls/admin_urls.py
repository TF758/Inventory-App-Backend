# db_inventory/api/admin_urls.py
from django.urls import path

from db_inventory.viewsets import asset_returns_viewset

urlpatterns = [

    # -------------------------
    # Item workflow (specific first)
    # -------------------------
    path( "return-request-items/<str:public_id>/approve/", asset_returns_viewset.AdminReturnRequestItemWorkflowViewSet.as_view({"post": "approve"}), name="admin-return-request-item-approve", ),
    path( "return-request-items/<str:public_id>/deny/", asset_returns_viewset.AdminReturnRequestItemWorkflowViewSet.as_view({"post": "deny"}), name="admin-return-request-item-deny", ),

    # -------------------------
    # Return Requests (Admin)
    # -------------------------
    path( "return-requests/", asset_returns_viewset.AdminReturnRequestViewSet.as_view({"get": "list"}), name="admin-return-request-list", ),
    path( "return-requests/pending/", asset_returns_viewset.AdminReturnRequestViewSet.as_view({"get": "pending"}), name="admin-return-request-pending", ),


    # Request workflow
    path( "return-requests/<str:public_id>/approve/", asset_returns_viewset.AdminReturnRequestWorkflowViewSet.as_view({"post": "approve"}), name="admin-return-request-approve", ),
    path( "return-requests/<str:public_id>/deny/", asset_returns_viewset.AdminReturnRequestWorkflowViewSet.as_view({"post": "deny"}), name="admin-return-request-deny", ),
    path( "return-requests/<str:public_id>/process/", asset_returns_viewset.AdminReturnRequestWorkflowViewSet.as_view({"post": "process"}), name="admin-return-request-process", ),
    path( "return-requests/<str:public_id>/", asset_returns_viewset.AdminReturnRequestViewSet.as_view({"get": "retrieve"}), name="admin-return-request-detail", ),
]