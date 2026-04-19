from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from core.filters import SelfAccessoryFilter, SelfConsumableFilter, SelfEquipmentFilter, MixAssetFilter
from core.pagination import FlexiblePagination
from django.db.models import Count
from rest_framework.viewsets import GenericViewSet
from rest_framework.mixins import RetrieveModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.mixins import ListModelMixin
from users.models.users import User
from rest_framework.generics import RetrieveAPIView
from core.utils.query_helpers import accessory_active_q, consumable_active_q, equipment_active_q, get_user_accessories, get_user_accessories_with_meta, get_user_consumables, get_user_consumables_with_meta, get_user_equipment, get_user_equipment_assignments, get_user_equipment_with_meta
from django.db.models import Exists, OuterRef,  Subquery, Sum,  F, IntegerField, Value
from django.db.models.functions import Coalesce, Greatest
from assignments.models.asset_assignment import ReturnRequest, ReturnRequestItem
from core.utils.asset_helpers import SelfAssetBuilder
from django.core.exceptions import ValidationError
from django.core.cache import cache
from rest_framework.response import Response
from users.api.serializers.self import SelfAccessoryAssignmentSerializer, SelfAssetSerializer, SelfAssignedEquipmentSerializer, SelfConsumableIssueSerializer, SelfUserProfileSerializer


class SelfUserProfileViewSet(RetrieveModelMixin, GenericViewSet):
    """
    Retrieve the profile of the currently authenticated user.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = SelfUserProfileSerializer

    queryset = (
        User.objects
        .filter(is_active=True)
        .annotate(
            equipment_count=Count(
                "equipment_assignments__equipment",
                filter=equipment_active_q(),
                distinct=True,
            ),
            accessory_count=Count(
                "accessory_assignments__accessory",
                filter=accessory_active_q(),
                distinct=True,
            ),
            consumable_count=Count(
                "consumable_assignments__consumable",
                filter=consumable_active_q(),
                distinct=True,
            ),
        )
    )

    def get_object(self):
        return self.queryset.get(pk=self.request.user.pk)
    

class SelfAssignedEquipmentViewSet(ListModelMixin, GenericViewSet):
    """
    List equipment currently assigned to the authenticated user.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = SelfAssignedEquipmentSerializer  
    pagination_class = FlexiblePagination

    pagination_class = FlexiblePagination

    filter_backends = [DjangoFilterBackend]
    filterset_class = SelfEquipmentFilter

    def get_queryset(self):

        pending_return_requests = ReturnRequestItem.objects.filter(
            equipment_assignment=OuterRef("pk"),
            return_request__status=ReturnRequest.Status.PENDING
        )

        return (
            get_user_equipment_assignments(self.request.user)
            .select_related(
                "equipment",
                "equipment__room",
                "equipment__room__location",
                "equipment__room__location__department",
            )
            .annotate(
                has_pending_return_request=Exists(pending_return_requests)
            )
            .order_by("-assigned_at")
        )

class SelfAccessoryViewSet(ListModelMixin, GenericViewSet):

    serializer_class = SelfAccessoryAssignmentSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = FlexiblePagination

    filter_backends = [DjangoFilterBackend]
    filterset_class = SelfAccessoryFilter

    def get_queryset(self):

        pending_items = ReturnRequestItem.objects.filter(
            accessory_assignment=OuterRef("pk"),
            return_request__status=ReturnRequest.Status.PENDING,
        )

        pending_qty_subquery = (
            pending_items
            .values("accessory_assignment")
            .annotate(total=Sum("quantity"))
            .values("total")
        )

        queryset = (
            get_user_accessories(self.request.user)
            .select_related(
                "accessory",
                "accessory__room",
                "accessory__room__location",
            )
            .annotate(
                pending_return_quantity=Coalesce(
                    Subquery(pending_qty_subquery[:1], output_field=IntegerField()),
                    Value(0),
                ),
            )
            .annotate(
                has_pending_return_request=Exists(pending_items),
                available_return_quantity=Greatest(
                    F("quantity") - F("pending_return_quantity"),
                    Value(0),
                ),
            )
            .order_by("-assigned_at")
        )

        return queryset
    
class SelfConsumableViewSet(ListModelMixin, GenericViewSet):

    serializer_class = SelfConsumableIssueSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = FlexiblePagination

    filter_backends = [DjangoFilterBackend]
    filterset_class = SelfConsumableFilter

    def get_queryset(self):

        pending_items = ReturnRequestItem.objects.filter(
            consumable_issue=OuterRef("pk"),
            return_request__status=ReturnRequest.Status.PENDING,
        )

        pending_qty_subquery = (
            pending_items
            .values("consumable_issue")
            .annotate(total=Sum("quantity"))
            .values("total")
        )

        return (
            get_user_consumables(self.request.user)
            .select_related(
                "consumable",
                "consumable__room",
                "consumable__room__location",
            )
            .annotate(
                pending_return_quantity=Coalesce(
                    Subquery(pending_qty_subquery[:1], output_field=IntegerField()),
                    Value(0),
                ),
            )
            .annotate(
                has_pending_return_request=Exists(pending_items),
                available_return_quantity=Greatest(
                    F("quantity") - F("pending_return_quantity"),
                    Value(0),
                ),
            )
            .order_by("-assigned_at")
        )


class SelfConsumableAssignmentDetailView(RetrieveAPIView):
    serializer_class = SelfConsumableIssueSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return get_object_or_404(
            get_user_consumables(self.request.user),
            consumable__public_id=self.kwargs["public_id"],
        )

MAX_ACTIVE_ASSIGNMENTS = 1000


def _validate_user_asset_load(user):
    total = (
        get_user_equipment_assignments(user).count()
        + get_user_accessories(user).count()
        + get_user_consumables(user).count()
    )

    if total > MAX_ACTIVE_ASSIGNMENTS:
        raise ValidationError(
            "User exceeds maximum active asset assignments. "
            "Bulk assets should be assigned to a room/location."
        )
    

class SelfAllAssetsViewSet(ListModelMixin, GenericViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = SelfAssetSerializer
    pagination_class = FlexiblePagination

    queryset = []

    def list(self, request, *args, **kwargs):
        user = request.user
        cache_key = f"user_assets:{user.id}:{request.get_full_path()}"

        # cached = cache.get(cache_key)
        # if cached:
        #     return Response(cached)

        _validate_user_asset_load(user)

        asset_types = request.query_params.getlist("asset_type")

        if not asset_types:
            asset_types = ["equipment", "accessory", "consumable"]

        equipment_qs = get_user_equipment_with_meta(user) if "equipment" in asset_types else []
        accessory_qs = get_user_accessories_with_meta(user) if "accessory" in asset_types else []
        consumable_qs = get_user_consumables_with_meta(user) if "consumable" in asset_types else []

        data = (
            [SelfAssetBuilder.from_equipment(e) for e in equipment_qs]
            + [SelfAssetBuilder.from_accessory(a) for a in accessory_qs]
            + [SelfAssetBuilder.from_consumable(c) for c in consumable_qs]
        )

        data = MixAssetFilter(request.query_params, data).filter()

        ordering = request.query_params.get("ordering", "-assigned_at")
        reverse = ordering.startswith("-")
        field = ordering.lstrip("-")

        if data and field not in data[0]:
            field = "assigned_at"

        data.sort(key=lambda x: x.get(field), reverse=reverse)

        page = self.paginate_queryset(data)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            response = self.get_paginated_response(serializer.data)

            cache.set(cache_key, response.data, timeout=60)
            return response

        serializer = self.get_serializer(data, many=True)
        # cache.set(cache_key, serializer.data, timeout=60)

        return Response(serializer.data)