from django.urls import path

from assignments.api.viewsets.consumable_assignment import UseConsumableView
from assignments.api.viewsets import asset_returns_viewset
from users.api.viewsets import self_viewsets
from users.api.viewsets.userprofile_viewsets import UserProfileViewSet

urlpatterns = [

    # Todo - Thessse routes were previously me/* now they parent route is self/*, 
    #update frontend url accordingly

    # User Viewing thier own profile and assets

    path( "", self_viewsets.SelfUserProfileViewSet.as_view({"get": "retrieve"}), name="self-user-profile" ),

    path( "assets/", self_viewsets.SelfAllAssetsViewSet.as_view({"get": "list"}), name="self-user-assets", ),

    path( "assets/return/", asset_returns_viewset.MixedAssetReturnViewSet.as_view({"post": "create"}), name="self-return-assets", ),

    path( "equipment/", self_viewsets.SelfAssignedEquipmentViewSet.as_view({"get": "list"}), name="self-user-equipment" ),

    path( "accessories/", self_viewsets.SelfAccessoryViewSet.as_view({"get": "list"}), name="self-user-accessories" ),

    path( "consumables/", self_viewsets.SelfConsumableViewSet.as_view({"get": "list"}), name="self-user-consumables" ),

    # -------------------------
    # Consumable usage (by user)
    # -------------------------

    path( "consumables/use/", UseConsumableView.as_view(), name="use-consumable" ),


    # -------------------------
    # Return Requests
    # -------------------------

    path( "returns/", asset_returns_viewset.SelfReturnRequestViewSet.as_view({"get": "list"}), name="self-return-requests", ),

    path( "returns/<str:public_id>/", asset_returns_viewset.SelfReturnRequestViewSet.as_view({"get": "retrieve"}), name="self-return-request-detail", ),
    

    path( "consumables/<str:public_id>/", self_viewsets.SelfConsumableAssignmentDetailView.as_view(), name="assign-consumable-detail" ),
    # -------------------------
    # Admin Profile
    # -------------------------

    path( "<str:public_id>/", UserProfileViewSet.as_view({"get": "retrieve"}), name="user-profile-detail" ),

]