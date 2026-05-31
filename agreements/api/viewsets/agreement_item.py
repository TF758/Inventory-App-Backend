from rest_framework.exceptions import ValidationError
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from agreements.models.agreements import  AssetAgreementItem
from core.mixins import AuditMixin, ScopeFilterMixin
from core.pagination import FlexiblePagination
from agreements.api.serialziers.agreement_item import AssetAgreementItemSerializer, AssetAgreementItemWriteSerializer
from agreements.services.coverage import can_attach_asset_to_agreement
from core.models.audit import AuditLog
from rest_framework import status


class AssetAgreementItemViewSet(AuditMixin, ScopeFilterMixin, viewsets.GenericViewSet, ):

    queryset = (
        AssetAgreementItem.objects
        .select_related(
            "agreement",
            "equipment",
            "consumable",
            "accessory",
        )
        .order_by("id")
    )

    pagination_class = FlexiblePagination

    lookup_field = "public_id"

    def get_serializer_class(self):
        if self.action == "attach":
            return AssetAgreementItemWriteSerializer
        return AssetAgreementItemSerializer

    def list(self, request):

        queryset = self.filter_queryset( self.get_queryset() )

        page = self.paginate_queryset( queryset )

        serializer = self.get_serializer(
            page if page is not None else queryset,
            many=True,
            context={
                "request": request
            },
        )

        if page is not None:
            return self.get_paginated_response(
                serializer.data )

        return Response(
            serializer.data
        )

    # -------------------------
    # Retrieve
    # -------------------------

    def retrieve( self, request, public_id=None, ):

        item = self.get_object()
        serializer = self.get_serializer(
            item,
            context={
                "request": request
            },
        )

        return Response( serializer.data )

    # -------------------------
    # Attach Asset
    # -------------------------

    @action(
        detail=False,
        methods=["post"],
    )
    def attach(self, request):

        serializer = self.get_serializer(
            data=request.data,
            context={
                "request": request
            },
        )

        serializer.is_valid( raise_exception=True )

        validated_data = ( serializer.validated_data )

        agreement = validated_data[ "agreement" ]

        # --------------------------------
        # Resolve Asset
        # --------------------------------

        asset = validated_data["asset"]

        item = serializer.save()


        response_serializer = AssetAgreementItemSerializer(
            item,
            context={"request": request},
        )

        self.audit(
            AuditLog.Events.AGREEMENT_ITEM_ATTACHED,
            target=item,
            description=(
                f"Attached asset "
                f"{asset.public_id} "
                f"to agreement "
                f"{agreement.public_id}"
            ),
            metadata={
                "agreement_public_id":
                    agreement.public_id,
                "agreement_name":
                    agreement.name,
                "asset_public_id":
                    asset.public_id,
                "asset_name":
                    getattr(asset, "name", ""),
                "asset_type":
                    item.asset_type,
                "agreement_item_public_id":
                    item.public_id,
                "performed_by":
                    request.user.email,
            },
        )
        

        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED,
        )

    # -------------------------
    # Detach Asset
    # -------------------------

    @action(
        detail=True,
        methods=["post"],
    )
    def detach(
        self,
        request,
        public_id=None,
    ):

        item = self.get_object()
        asset = item.asset
        agreement = item.agreement

        # --------------------------------
        # Audit Log
        # --------------------------------

        self.audit(
            AuditLog.Events.AGREEMENT_ITEM_DETACHED,
            target=item,
            description=(
                f"{request.user.email} detached asset "
                f"{asset.public_id} "
                f"from agreement "
                f"{agreement.public_id}"
            ),
            metadata={
                "agreement_public_id":
                    agreement.public_id,

                "agreement_name":
                    agreement.name,

                "asset_public_id":
                    asset.public_id,

                "asset_name":
                    getattr(asset, "name", ""),

                "asset_type":
                    item.asset_type,

                "agreement_item_public_id":
                    item.public_id,

                "performed_by":
                    request.user.email,
            },
        )


        item.delete()

        return Response(
            {
                "detail":
                "Asset detached from agreement."
            },
            status=status.HTTP_200_OK,
        )