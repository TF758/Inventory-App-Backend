from django.shortcuts import get_object_or_404
from db_inventory.serializers.self import  SelfAccessoryAssignmentSerializer, SelfConsumableIssueSerializer, SelfUserProfileSerializer
from django_filters.rest_framework import DjangoFilterBackend
from db_inventory.filters import SelfAccessoryFilter, SelfConsumableFilter, SelfEquipmentFilter
from db_inventory.pagination import FlexiblePagination
from django.db.models import Count
from rest_framework.viewsets import GenericViewSet
from rest_framework.mixins import RetrieveModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.mixins import ListModelMixin
from db_inventory.serializers.self import SelfAssignedEquipmentSerializer
from db_inventory.models.users import User
from rest_framework.generics import RetrieveAPIView
from db_inventory.utils.query_helpers import accessory_active_q, consumable_active_q, equipment_active_q, get_user_accessories, get_user_consumables, get_user_equipment, get_user_equipment_assignments



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
        return (
            get_user_equipment_assignments(self.request.user)
            .select_related(
                "equipment",
                "equipment__room",
                "equipment__room__location",
                "equipment__room__location__department",
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
        return (
            get_user_accessories(self.request.user)
            .select_related(
                "accessory",
                "accessory__room",
                "accessory__room__location",
            )
            .order_by("-assigned_at")
        )
    
class SelfConsumableViewSet(ListModelMixin, GenericViewSet):

    serializer_class = SelfConsumableIssueSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = FlexiblePagination

    filter_backends = [DjangoFilterBackend]
    filterset_class = SelfConsumableFilter

    def get_queryset(self):
        return (
            get_user_consumables(self.request.user)
            .select_related(
                "consumable",
                "consumable__room",
                "consumable__room__location",
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