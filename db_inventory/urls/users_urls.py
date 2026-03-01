# db_inventory/urls/user_urls.py

from django.urls import path

from db_inventory.viewsets import user_viewsets


urlpatterns = [


    path("create-full/", user_viewsets.FullUserCreateView.as_view(), name="create-full-user"),

    path("unallocated/", user_viewsets.UnallocatedUserViewSet.as_view({ "get": "list", }), name="unallocated-user-list"),

    path("", user_viewsets.UserModelViewSet.as_view({ "get": "list", "post": "create" }), name="users"),
    path("<str:public_id>/", user_viewsets.UserModelViewSet.as_view({
        "get": "retrieve",
        "put": "update",
        "patch": "partial_update",
        "delete": "destroy"
    }), name="user-detail"),

    # ----------------------------
    # User Assets
    # ----------------------------
    path("<str:user_public_id>/equipment/", user_viewsets.UserEquipmentViewSet.as_view({"get": "list"}), name="user-equipment-list", ),

    path("<str:user_public_id>/accessories/", user_viewsets.UserAccessoryAssignmentViewSet.as_view({"get": "list"}), name="user-accessory-assignment-list", ),

    path("<str:user_public_id>/consumables/", user_viewsets.UserConsumableIssueViewSet.as_view({"get": "list"}), name="user-consumable-issue-list", ),

    # ----------------------------
    # User Locations
    # ----------------------------
    path("placement/", user_viewsets.UserLocationViewSet.as_view({
        "get": "list",
        "post": "create",
    }), name="userlocation-list"),

    path("placement/<str:public_id>/", user_viewsets.UserLocationViewSet.as_view({
        "get": "retrieve",
        "put": "update",
        "patch": "partial_update",
        "delete": "destroy",
    }), name="userlocation-detail"),

    path("<str:public_id>/current-placement/", user_viewsets.UserLocationByUserView.as_view(), name="user-current-location", ),

    # ----------------------------
    # Transfers
    # ----------------------------
    path("transfers/", user_viewsets.UserTransferViewSet.as_view({"post": "create"}), name="user-transfer", ),

    # ----------------------------
    # User Profile (Admin View)
    # ----------------------------
    path("profile/<str:public_id>/", user_viewsets.UserProfileViewSet.as_view({"get": "retrieve"}), name="user-profile-detail", ),

]