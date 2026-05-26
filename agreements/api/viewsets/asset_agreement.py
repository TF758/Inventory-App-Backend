from datetime import timedelta
from django.core.exceptions import ValidationError
from django.db.models import Count
from django.utils.timezone import now
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from agreements.api.serialziers.agreement_coverage import AgreementCoverageSerializer, AgreementCoverageWriteSerializer
from agreements.api.serialziers.agreement_history import AgreementHistorySerializer, AgreementItemHistorySerializer
from agreements.api.serialziers.asset_agreement import AssetAgreementSerializer, AssetAgreementWriteSerializer
from agreements.models.agreements import AgreementCoverage, AgreementHistory, AgreementItemHistory, AssetAgreement, AssetAgreementItem
from core.mixins import ScopeFilterMixin
from core.pagination import FlexiblePagination
from agreements.api.serialziers.agreement_item import AssetAgreementItemSerializer, AssetAgreementItemWriteSerializer, resolve_asset_by_public_id
from agreements.services.coverage import can_attach_asset_to_agreement


class AssetAgreementViewSet( ScopeFilterMixin, viewsets.ModelViewSet, ):

    queryset = (
        AssetAgreement.objects
        .select_related("managing_department")
        .prefetch_related(
            "coverages",
            "items",
            "history",
        )
        .annotate(
            item_count=Count("items", distinct=True),
            coverage_count=Count("coverages", distinct=True),
        )
        .order_by("id")
    )

    # permission_classes = [AssetAgreementPermission]

    pagination_class = FlexiblePagination
    lookup_field = "public_id"

    def get_serializer_class(self):

        if self.action in [
            "create",
            "update",
            "partial_update",
        ]:
            return AssetAgreementWriteSerializer
        return AssetAgreementSerializer

    @action(detail=True, methods=["get"])
    def coverages(self, request, public_id=None):

        agreement = self.get_object()

        queryset = (
            agreement.coverages
            .select_related(
                "department",
                "location",
                "room",
            )
            .order_by("id")
        )

        queryset = self.filter_queryset(
            queryset
        )

        page = self.paginate_queryset(
            queryset
        )

        serializer = AgreementCoverageSerializer(
            page if page is not None else queryset,
            many=True,
            context={"request": request},
        )

        if page is not None:

            return self.get_paginated_response(
                serializer.data
            )

        return Response(
            serializer.data
        )

    @action(detail=True, methods=["get"])
    def items(self, request, public_id=None):

        agreement = self.get_object()

        queryset = (
            agreement.items
            .select_related(
                "equipment",
                "consumable",
                "accessory",
            )
            .order_by("id")
        )

        queryset = self.filter_queryset( queryset )

        page = self.paginate_queryset( queryset )

        serializer = AssetAgreementItemSerializer(
            page if page is not None else queryset,
            many=True,
            context={
                "request": request,
            },
        )

        if page is not None:

            return self.get_paginated_response(
                serializer.data
            )

        return Response( serializer.data )

    # -------------------------
    # Agreement History
    # -------------------------

    @action(detail=True, methods=["get"])
    def history(self, request, public_id=None):

        agreement = self.get_object()

        serializer = AgreementHistorySerializer(
            agreement.history.all(),
            many=True,
            context={"request": request},
        )

        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def expiring(self, request):

        threshold = now().date() + timedelta(days=30)

        queryset = (
            self.get_queryset()
            .filter(
                expiry_date__isnull=False,
                expiry_date__lte=threshold,
            )
        )

        serializer = self.get_serializer(
            queryset,
            many=True,
            context={"request": request},
        )

        return Response(serializer.data)


    @action(detail=False, methods=["get"])
    def active(self, request):

        queryset = self.get_queryset().filter(
            status="ACTIVE",
        )

        serializer = self.get_serializer(
            queryset,
            many=True,
            context={"request": request},
        )

        return Response(serializer.data)


    @action(detail=False, methods=["get"])
    def expired(self, request):

        queryset = self.get_queryset().filter( status="EXPIRED", )
        serializer = self.get_serializer( queryset, many=True, context={"request": request}, )

        return Response(serializer.data)


    @action(
        detail=False,
        methods=["get"],
    )
    def applicable(self, request):

        asset_public_id = (
            request.query_params.get(
                "asset_public_id"
            )
        )

        if not asset_public_id:

            raise ValidationError(
                {
                    "asset_public_id":
                    "This field is required."
                }
            )

        asset = resolve_asset_by_public_id(
            asset_public_id
        )

        queryset = [
            agreement
            for agreement in self.get_queryset()
            if can_attach_asset_to_agreement(
                agreement=agreement,
                asset=asset,
            )
        ]

        page = self.paginate_queryset(
            queryset
        )

        serializer = self.get_serializer(
            page if page is not None else queryset,
            many=True,
            context={
                "request": request,
            },
        )

        if page is not None:

            return self.get_paginated_response(
                serializer.data
            )

        return Response(
            serializer.data
        )

class AgreementCoverageViewSet( ScopeFilterMixin, viewsets.ModelViewSet, ):

    queryset = (
        AgreementCoverage.objects
        .select_related(
            "agreement",
            "department",
            "location",
            "room",
        )
        .order_by("id")
    )

    # permission_classes = [AssetAgreementPermission]

    pagination_class = FlexiblePagination

    lookup_field = "public_id"

    def get_serializer_class(self):
        if self.action in [
            "create",
            "update",
            "partial_update",
        ]:
            return AgreementCoverageWriteSerializer
        return AgreementCoverageSerializer


class AssetAgreementItemViewSet( ScopeFilterMixin, viewsets.GenericViewSet, ):

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

    # -------------------------
    # Serializer Selection
    # -------------------------

    def get_serializer_class(self):
        if self.action == "attach":
            return AssetAgreementItemWriteSerializer
        return AssetAgreementItemSerializer

    # -------------------------
    # List
    # -------------------------

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

        serializer.is_valid(
            raise_exception=True
        )

        validated_data = (
            serializer.validated_data
        )

        agreement = validated_data[
            "agreement"
        ]

        # --------------------------------
        # Resolve Asset
        # --------------------------------

        asset = (
            validated_data.get(
                "equipment"
            )
            or
            validated_data.get(
                "accessory"
            )
            or
            validated_data.get(
                "consumable"
            )
        )

        # --------------------------------
        # Eligibility Check
        # --------------------------------

        if not can_attach_asset_to_agreement(
            agreement=agreement,
            asset=asset,
        ):

            raise ValidationError(
                {
                    "non_field_errors": [
                        (
                            "This asset does not "
                            "fall within the "
                            "agreement coverage "
                            "scope."
                        )
                    ]
                }
            )

        # --------------------------------
        # Save
        # --------------------------------

        item = serializer.save()

        response_serializer = (
            AssetAgreementItemSerializer(
                item,
                context={
                    "request": request
                },
            )
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

        item.delete()

        return Response(
            {
                "detail":
                "Asset detached from agreement."
            },
            status=status.HTTP_200_OK,
        )
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