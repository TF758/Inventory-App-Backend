from datetime import timedelta
from rest_framework.exceptions import ValidationError
from django.db.models import Q, Count
from django.utils.timezone import now
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from agreements.api.serialziers.agreement_coverage import AgreementCoverageSerializer
from agreements.api.serialziers.agreement_history import AgreementHistorySerializer
from agreements.api.serialziers.asset_agreement import AssetAgreementSerializer, AssetAgreementWriteSerializer
from agreements.models.agreements import  AgreementHistory, AssetAgreement,  CoverageScopeType
from core.mixins import ScopeFilterMixin
from core.pagination import FlexiblePagination
from agreements.api.serialziers.agreement_item import AssetAgreementItemSerializer, resolve_asset_by_public_id
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
