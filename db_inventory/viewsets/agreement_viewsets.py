
from db_inventory.mixins import ScopeFilterMixin
from assets.models.assets import AssetAgreement, AssetAgreementItem
from db_inventory.serializers.agreement import AssetAgreementItemSerializer, AssetAgreementItemWriteSerializer, AssetAgreementSerializer, AssetAgreementWriteSerializer
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from datetime import timedelta
from django.utils.timezone import now

from db_inventory.permissions.assets import AssetAgreementPermission
from db_inventory.pagination import FlexiblePagination


class AssetAgreementViewSet(ScopeFilterMixin, viewsets.ModelViewSet):

    queryset = AssetAgreement.objects.prefetch_related("items").order_by("id")
    permission_classes = [AssetAgreementPermission]
    pagination_class = FlexiblePagination
    lookup_field = "public_id"

    def get_serializer_class(self):

        if self.action in ["create", "update", "partial_update"]:
            return AssetAgreementWriteSerializer

        return AssetAgreementSerializer

    @action(detail=True, methods=["get"])
    def assets(self, request, public_id=None):

        agreement = self.get_object()

        items = agreement.items.select_related(
            "agreement",
            "equipment",
            "consumable",
            "accessory",
        )

        serializer = AssetAgreementItemSerializer(
            items,
            many=True,
            context={"request": request}
        )

        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def expiring(self, request):

        threshold = now().date() + timedelta(days=30)

        qs = self.get_queryset().filter(expiry_date__lte=threshold)

        serializer = self.get_serializer(qs, many=True)

        return Response(serializer.data)

class AssetAgreementItemViewSet(ScopeFilterMixin, viewsets.ModelViewSet):

    queryset = AssetAgreementItem.objects.select_related(
        "agreement",
        "equipment",
        "consumable",
        "accessory",
    ).order_by("id")

    permission_classes = [AssetAgreementPermission]
    pagination_class = FlexiblePagination

    def get_serializer_class(self):

        if self.action in ["create", "update", "partial_update"]:
            return AssetAgreementItemWriteSerializer

        return AssetAgreementItemSerializer