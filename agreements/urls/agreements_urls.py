from django.urls import path

from agreements.api.viewsets.asset_agreement import ( AgreementCoverageViewSet, AgreementHistoryViewSet, AgreementItemHistoryViewSet, AssetAgreementItemViewSet, AssetAgreementViewSet, )

urlpatterns = [

    # =================================================
    # Agreement Collections
    # =================================================

    path( "", AssetAgreementViewSet.as_view({ "get": "list", "post": "create", }), name="agreements", ),

    path( "active/", AssetAgreementViewSet.as_view({ "get": "active", }), name="active-agreements", ),

    path( "expired/", AssetAgreementViewSet.as_view({ "get": "expired", }), name="expired-agreements", ),

    path( "expiring/", AssetAgreementViewSet.as_view({ "get": "expiring", }), name="expiring-agreements", ),

    path( "applicable/", AssetAgreementViewSet.as_view({ "get": "applicable", }), name="applicable-agreements", ),

    # =================================================
    # Coverage Rules
    # =================================================

    path( "coverages/", AgreementCoverageViewSet.as_view({ "get": "list", "post": "create", }), name="coverages", ),

    path( "coverages/<str:public_id>/", AgreementCoverageViewSet.as_view({ "get": "retrieve", "put": "update", "patch": "partial_update", "delete": "destroy", }), name="coverage-detail", ),

    # =================================================
    # Agreement Items
    # =================================================

    path( "items/", AssetAgreementItemViewSet.as_view({ "get": "list", }), name="agreement-items-list", ),

    path( "items/attach/", AssetAgreementItemViewSet.as_view({ "post": "attach", }), name="attach-agreement-item", ),

    path( "items/<str:public_id>/", AssetAgreementItemViewSet.as_view({ "get": "retrieve", }), name="agreement-item-detail", ),

    path( "items/<str:public_id>/detach/", AssetAgreementItemViewSet.as_view({ "post": "detach", }), name="detach-agreement-item", ),

    # =================================================
    # Agreement History
    # =================================================

    path( "history/", AgreementHistoryViewSet.as_view({ "get": "list", }), name="agreement-history-list", ),

    path( "history/<int:pk>/", AgreementHistoryViewSet.as_view({ "get": "retrieve", }), name="agreement-history-detail", ),

    # =================================================
    # Agreement Item History
    # =================================================

    path(
        "item-history/",
        AgreementItemHistoryViewSet.as_view({
            "get": "list",
        }),
        name="agreement-item-history-list",
    ),

    path(
        "item-history/<int:pk>/",
        AgreementItemHistoryViewSet.as_view({
            "get": "retrieve",
        }),
        name="agreement-item-history-detail",
    ),

    # =================================================
    # Agreement Detail Routes

    # =================================================

    path(
        "<str:public_id>/",
        AssetAgreementViewSet.as_view({
            "get": "retrieve",
            "put": "update",
            "patch": "partial_update",
            "delete": "destroy",
        }),
        name="agreement-detail",
    ),

    path(
        "<str:public_id>/coverages/",
        AssetAgreementViewSet.as_view({
            "get": "coverages",
        }),
        name="agreement-coverages",
    ),

    path(
        "<str:public_id>/items/",
        AssetAgreementViewSet.as_view({
            "get": "items",
        }),
        name="agreement-items",
    ),

    path(
        "<str:public_id>/history/",
        AssetAgreementViewSet.as_view({
            "get": "history",
        }),
        name="agreement-history",
    ),
]