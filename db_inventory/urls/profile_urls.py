# db_inventory/urls/profile_urls.py

from django.urls import path
from db_inventory.viewsets import self_viewsets
from db_inventory.viewsets.asset_assignment.consumable_assignment import UseConsumableView
from db_inventory.viewsets.user_viewsets import UserProfileViewSet

urlpatterns = [

    # Self Profile
    path("me/", self_viewsets.SelfUserProfileViewSet.as_view({"get": "retrieve"}), name="self-user-profile"),

    path("me/equipment/", self_viewsets.SelfAssignedEquipmentViewSet.as_view({"get": "list"}), name="self-user-equipment"),

    path("me/accessories/", self_viewsets.SelfAccessoryViewSet.as_view({"get": "list"}), name="self-user-accessories"),

    path("me/consumables/", self_viewsets.SelfConsumableViewSet.as_view({"get": "list"}), name="self-user-consumables"),

    path("me/consumables/use/", UseConsumableView.as_view(), name="use-consumable"),
    path("me/consumables/<str:public_id>/", self_viewsets.SelfConsumableAssignmentDetailView.as_view(), name="assign-consumable-detail"),

    # Admin profile view
    path("<str:public_id>/", UserProfileViewSet.as_view({"get": "retrieve"}), name="user-profile-detail"),
]