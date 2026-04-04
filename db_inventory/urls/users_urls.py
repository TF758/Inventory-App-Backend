# db_inventory/urls/user_urls.py

from django.urls import path

from db_inventory.viewsets import user_viewsets


urlpatterns = [

    # ----------------------------
    # Static Routes FIRST
    # ----------------------------
    path("create-full/", user_viewsets.FullUserCreateView.as_view(), name='create-full-user'),
    path("unallocated/", user_viewsets.UnallocatedUserViewSet.as_view({"get": "list"}), name="unassigned-users"),

    # Placement
    path("placement/", user_viewsets.UserPlacementViewSet.as_view({
        "get": "list",
        "post": "create",
    }), name='userlocation-list-create' ),
    path("placement/<str:public_id>/", user_viewsets.UserPlacementViewSet.as_view({
        "get": "retrieve",
        "put": "update",
        "patch": "partial_update",
        "delete": "destroy",
    }), name='userlocation-detail'),

    # Transfers
    path("transfers/", user_viewsets.UserTransferViewSet.as_view({"post": "create"})),

    # Profile
    path("profile/<str:public_id>/", user_viewsets.UserProfileViewSet.as_view({"get": "retrieve"}), name='user-profile-detail'),

    # Assets
    path("<str:user_public_id>/equipment/", user_viewsets.UserEquipmentViewSet.as_view({"get": "list"})),
    path("<str:user_public_id>/accessories/", user_viewsets.UserAccessoryAssignmentViewSet.as_view({"get": "list"})),
    path("<str:user_public_id>/consumables/", user_viewsets.UserConsumableIssueViewSet.as_view({"get": "list"})),

    # Current placement
    path("<str:user_public_id>/current-placement/", user_viewsets.UserPlacementByUserView.as_view()),

    path("<str:user_public_id>/asset-status/", user_viewsets.UserAssetStatusView.as_view(), name="user-asset-status"),

    # ----------------------------
    # Generic user routes LAST
    # ----------------------------
    path("", user_viewsets.UserModelViewSet.as_view({
        "get": "list",
        "post": "create",
    }), name='users'),
    path("<str:public_id>/", user_viewsets.UserModelViewSet.as_view({
        "get": "retrieve",
        "put": "update",
        "patch": "partial_update",
        "delete": "destroy",
    }),  name='user-detail'),
]