from db_inventory.serializers.self import  SelfUserProfileSerializer
from django_filters.rest_framework import DjangoFilterBackend
from db_inventory.filters import EquipmentAssignmentFilter
from db_inventory.pagination import FlexiblePagination
from django.db.models import Count, Q
from rest_framework.viewsets import GenericViewSet
from rest_framework.mixins import RetrieveModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.mixins import ListModelMixin
from db_inventory.models.asset_assignment import EquipmentAssignment
from db_inventory.serializers.self import SelfAssignedEquipmentSerializer
from db_inventory.models.users import User


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
                "equipment_assignments",
                filter=Q(
                    equipment_assignments__returned_at__isnull=True
                ),
                distinct=True,
            ),
            accessory_count=Count(
                "accessory_assignments__accessory",
                filter=Q(
                    accessory_assignments__returned_at__isnull=True,
                    accessory_assignments__quantity__gt=0,
                ),
                distinct=True,
            ),
            consumable_count=Count(
                "consumable_assignments__consumable",
                filter=Q(
                    consumable_assignments__returned_at__isnull=True,
                    consumable_assignments__quantity__gt=0,
                ),
                distinct=True,
            ),
        )
    )

    def get_object(self):
        # No lookup, no scope checks — self only
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
    filterset_class = EquipmentAssignmentFilter

    def get_queryset(self):
       return (
        EquipmentAssignment.objects
        .filter(
            user=self.request.user,
            returned_at__isnull=True,
        )
        .select_related(
            "equipment",
            "equipment__room",
            "equipment__room__location",
            "equipment__room__location__department",
        )
        .order_by("-assigned_at")
    )
