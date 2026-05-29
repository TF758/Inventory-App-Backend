from rest_framework import viewsets
from agreements.api.serialziers.agreement_history import AgreementHistorySerializer, AgreementItemHistorySerializer
from agreements.models.agreements import AgreementHistory, AgreementItemHistory
from core.mixins import ScopeFilterMixin
from core.pagination import FlexiblePagination


class AgreementHistoryViewSet( ScopeFilterMixin, viewsets.ReadOnlyModelViewSet, ):

    queryset = (
        AgreementHistory.objects
        .select_related(
            "agreement",
            "user",
        )
        .order_by("-created_at")
    )

    # permission_classes = [AssetAgreementPermission]

    serializer_class = AgreementHistorySerializer

    pagination_class = FlexiblePagination

    lookup_field = "id"

class AgreementItemHistoryViewSet(
    ScopeFilterMixin,
    viewsets.ReadOnlyModelViewSet,
):

    queryset = (
        AgreementItemHistory.objects
        .select_related(
            "agreement",
            "agreement_item",
            "user",
        )
        .order_by("-created_at")
    )

    # permission_classes = [AssetAgreementPermission]

    serializer_class = AgreementItemHistorySerializer

    pagination_class = FlexiblePagination

    lookup_field = "id"