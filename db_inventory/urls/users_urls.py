# db_inventory/urls/user_urls.py

from django.urls import path

from db_inventory.viewsets import user_viewsets


urlpatterns = [

    # ----------------------------
    # Static Routes FIRST
    # ----------------------------
    path("create-full/", user_viewsets.FullUserCreateView.as_view()),
    path("unallocated/", user_viewsets.UnallocatedUserViewSet.as_view({"get": "list"})),

    # Placement
    path("placement/", user_viewsets.UserLocationViewSet.as_view({
        "get": "list",
        "post": "create",
    })),
    path("placement/<str:public_id>/", user_viewsets.UserLocationViewSet.as_view({
        "get": "retrieve",
        "put": "update",
        "patch": "partial_update",
        "delete": "destroy",
    })),

    # Transfers
    path("transfers/", user_viewsets.UserTransferViewSet.as_view({"post": "create"})),

    # Profile
    path("profile/<str:public_id>/", user_viewsets.UserProfileViewSet.as_view({"get": "retrieve"})),

    # Assets
    path("<str:user_public_id>/equipment/", user_viewsets.UserEquipmentViewSet.as_view({"get": "list"})),
    path("<str:user_public_id>/accessories/", user_viewsets.UserAccessoryAssignmentViewSet.as_view({"get": "list"})),
    path("<str:user_public_id>/consumables/", user_viewsets.UserConsumableIssueViewSet.as_view({"get": "list"})),

    # Current placement
    path("<str:user_public_id>/current-placement/", user_viewsets.UserLocationByUserView.as_view()),

    # ----------------------------
    # Generic user routes LAST
    # ----------------------------
    path("", user_viewsets.UserModelViewSet.as_view({
        "get": "list",
        "post": "create",
    })),
    path("<str:public_id>/", user_viewsets.UserModelViewSet.as_view({
        "get": "retrieve",
        "put": "update",
        "patch": "partial_update",
        "delete": "destroy",
    })),
]