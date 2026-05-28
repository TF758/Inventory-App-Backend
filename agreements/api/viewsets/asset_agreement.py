from datetime import timedelta
from rest_framework.exceptions import ValidationError
from django.db.models import Q, Count
from django.utils.timezone import now
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from agreements.api.serialziers.agreement_coverage import AgreementCoverageSerializer, AgreementCoverageWriteSerializer
from agreements.api.serialziers.agreement_history import AgreementHistorySerializer, AgreementItemHistorySerializer
from agreements.api.serialziers.asset_agreement import AssetAgreementSerializer, AssetAgreementWriteSerializer
from agreements.models.agreements import AgreementCoverage, AgreementHistory, AgreementItemHistory, AssetAgreement, AssetAgreementItem, CoverageScopeType
from core.mixins import AuditMixin, ScopeFilterMixin
from core.pagination import FlexiblePagination
from agreements.api.serialziers.agreement_item import AssetAgreementItemSerializer, AssetAgreementItemWriteSerializer, resolve_asset_by_public_id
from agreements.services.coverage import can_attach_asset_to_agreement
from assets.models.assets import Accessory, Consumable, Equipment


class AssetAgreementViewSet( ScopeFilterMixin, viewsets.ModelViewSet, ):

    queryset = (
        AssetAgreement.objects
        .select_related(
            "managing_department"
        )
        .annotate(
            item_count=Count(
                "items",
                distinct=True,
            ),
            coverage_count=Count(
                "coverages",
                distinct=True,
            ),
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
    
    def create(self, request, *args, **kwargs):

        serializer = self.get_serializer(
            data=request.data,
            context={
                "request": request
            },
        )

        serializer.is_valid(
            raise_exception=True
        )

        agreement = serializer.save()
        # --------------------------------
        # Create History Record
        # --------------------------------

        AgreementHistory.objects.create(
            agreement=agreement,
            event_type=AgreementHistory.EventType.CREATED,
            new_status=agreement.status,
            new_expiry_date=agreement.expiry_date,
            new_renewal_date=agreement.renewal_date,
            notes="Agreement created.",
            user=request.user,
            user_email=request.user.email,
        )

        # --------------------------------
        # Audit Log
        # --------------------------------

        self.audit(
            AuditLog.Events.AGREEMENT_CREATED,
            target=agreement,
            description=(
                f"{request.user.email} created "
                f"agreement "
                f"{agreement.public_id}"
            ),
            metadata={
                "agreement_public_id":
                    agreement.public_id,

                "agreement_name":
                    agreement.name,

                "agreement_type":
                    agreement.agreement_type,

                "agreement_status":
                    agreement.status,

                "vendor":
                    agreement.vendor,

                "performed_by":
                    request.user.email,
            },
        )

        response_serializer = (
            AssetAgreementSerializer(
                agreement,
                context={
                    "request": request
                },
            )
        )

        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED,
        )

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

        asset_public_id = request.query_params.get(
            "asset_public_id"
        )

        if not asset_public_id:

            raise ValidationError({
                "asset_public_id":
                "This field is required."
            })

        asset = resolve_asset_by_public_id(
            asset_public_id
        )

        room = getattr(
            asset,
            "room",
            None,
        )

        if not room:

            return self.get_paginated_response([])

        location = room.location

        department = (
            location.department
            if location
            else None
        )

        queryset = (
            self.get_queryset()
            .filter(
                Q(
                    coverages__scope_type=CoverageScopeType.GLOBAL,
                )
                |
                Q(
                    coverages__scope_type=CoverageScopeType.ROOM,
                    coverages__room=room,
                )
                |
                Q(
                    coverages__scope_type=CoverageScopeType.LOCATION,
                    coverages__location=location,
                )
                |
                Q(
                    coverages__scope_type=CoverageScopeType.DEPARTMENT,
                    coverages__department=department,
                )
            )
            .distinct()
        )

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
        
    # -------------------------
    # Agreements By Asset
    # -------------------------

    @action(
        detail=False,
        methods=["get"],
    )
    def by_asset(self, request):

        asset_public_id = (
            request.query_params.get(
                "asset_public_id"
            )
        )

        if not asset_public_id:

            raise ValidationError({
                "asset_public_id":
                "This field is required."
            })

        # --------------------------------
        # Resolve Asset
        # --------------------------------

        asset = resolve_asset_by_public_id(
            asset_public_id
        )

        # --------------------------------
        # Query Agreements
        # --------------------------------

        queryset = (
            AssetAgreement.objects.none()
        )

        if isinstance(asset, Equipment):

            queryset = (
                self.get_queryset().filter(
                    items__equipment=asset
                )
            )

        elif isinstance(asset, Consumable):

            queryset = (
                self.get_queryset().filter(
                    items__consumable=asset
                )
            )

        elif isinstance(asset, Accessory):

            queryset = (
                self.get_queryset().filter(
                    items__accessory=asset
                )
            )

        queryset = (
            queryset
            .distinct()
            .order_by("name")
        )

        # --------------------------------
        # Pagination
        # --------------------------------

        page = self.paginate_queryset(
            queryset
        )

        serializer = self.get_serializer(
            page if page is not None else queryset,
            many=True,
            context={
                "request": request
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
    
       # -------------------------
    # Create
    # -------------------------

    def create(self, request, *args, **kwargs):

        serializer = self.get_serializer(
            data=request.data,
            context={
                "request": request
            },
        )

        serializer.is_valid(
            raise_exception=True
        )

        coverage = serializer.save()

        # --------------------------------
        # Resolve Scope Label
        # --------------------------------

        scope_target = (
            coverage.department
            or coverage.location
            or coverage.room
            or "GLOBAL"
        )

        # --------------------------------
        # Audit Log
        # --------------------------------

        self.audit(
            AuditLog.Events.AGREEMENT_COVERAGE_CREATED,
            target=coverage,
            description=(
                f"{request.user.email} added "
                f"{coverage.scope_type} coverage "
                f"to agreement "
                f"{coverage.agreement.public_id}"
            ),
            metadata={
                "agreement_public_id":
                    coverage.agreement.public_id,

                "agreement_name":
                    coverage.agreement.name,

                "coverage_public_id":
                    coverage.public_id,

                "scope_type":
                    coverage.scope_type,

                "scope_target":
                    str(scope_target),

                "performed_by":
                    request.user.email,
            },
        )

        response_serializer = (
            AgreementCoverageSerializer(
                coverage,
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
    # Destroy
    # -------------------------

    def destroy( self, request, *args, **kwargs, ):

        coverage = self.get_object()

        scope_target = (
            coverage.department
            or coverage.location
            or coverage.room
            or "GLOBAL"
        )

        # --------------------------------
        # Audit Log
        # --------------------------------

        self.audit(
            AuditLog.Events.AGREEMENT_COVERAGE_REMOVED,
            target=coverage,
            description=(
                f"{request.user.email} removed "
                f"{coverage.scope_type} coverage "
                f"from agreement "
                f"{coverage.agreement.public_id}"
            ),
            metadata={
                "agreement_public_id":
                    coverage.agreement.public_id,
                "agreement_name":
                    coverage.agreement.name,
                "coverage_public_id":
                    coverage.public_id,
                "scope_type":
                    coverage.scope_type,
                "scope_target":
                    str(scope_target),
                "performed_by":
                    request.user.email,
            },
        )

        coverage.delete()

        return Response(
            status=status.HTTP_204_NO_CONTENT,
        )


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