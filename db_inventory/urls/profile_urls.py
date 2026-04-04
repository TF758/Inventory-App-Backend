# db_inventory/urls/profile_urls.py

from django.urls import path
from db_inventory.viewsets import self_viewsets, asset_returns_viewset
from db_inventory.viewsets.asset_assignment.consumable_assignment import UseConsumableView
from db_inventory.viewsets.user_viewsets import UserProfileViewSet

urlpatterns = [

    # -------------------------
    # Self Profile
    # -------------------------

    path( "me/", self_viewsets.SelfUserProfileViewSet.as_view({"get": "retrieve"}), name="self-user-profile" ),

    path( "me/assets/", self_viewsets.SelfAllAssetsViewSet.as_view({"get": "list"}), name="self-user-assets", ),

    path( "me/assets/return/", asset_returns_viewset.MixedAssetReturnViewSet.as_view({"post": "create"}), name="self-return-assets", ),

    path( "me/equipment/", self_viewsets.SelfAssignedEquipmentViewSet.as_view({"get": "list"}), name="self-user-equipment" ),

    path( "me/accessories/", self_viewsets.SelfAccessoryViewSet.as_view({"get": "list"}), name="self-user-accessories" ),

    path( "me/consumables/", self_viewsets.SelfConsumableViewSet.as_view({"get": "list"}), name="self-user-consumables" ),

    # -------------------------
    # Consumable usage
    # -------------------------

    path( "me/consumables/use/", UseConsumableView.as_view(), name="use-consumable" ),



    # -------------------------
    # Return Requests
    # -------------------------

    path( "me/returns/", asset_returns_viewset.SelfReturnRequestViewSet.as_view({"get": "list"}), name="self-return-requests", ),

    path( "me/returns/<str:public_id>/", asset_returns_viewset.SelfReturnRequestViewSet.as_view({"get": "retrieve"}), name="self-return-request-detail", ),
    

    path( "me/consumables/<str:public_id>/", self_viewsets.SelfConsumableAssignmentDetailView.as_view(), name="assign-consumable-detail" ),
    # -------------------------
    # Admin Profile
    # -------------------------

    path(
        "<str:public_id>/",
        UserProfileViewSet.as_view({"get": "retrieve"}),
        name="user-profile-detail"
    ),

]