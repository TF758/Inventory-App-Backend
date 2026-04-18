
from django.shortcuts import get_object_or_404
from rest_framework import viewsets
from rest_framework import mixins
from db_inventory.pagination import FlexiblePagination
from db_inventory.permissions import UserPermission
from rest_framework.response import Response
from rest_framework.views import APIView
from db_inventory.permissions.helpers import filter_user_assets_by_scope
from django.db.models import Count
from rest_framework.viewsets import GenericViewSet
from rest_framework.mixins import RetrieveModelMixin
from db_inventory.permissions.users import CanViewUserProfile
from rest_framework import viewsets
from rest_framework.response import Response
from db_inventory.serializers.equipment import EquipmentSerializer
from db_inventory.utils.query_helpers import accessory_active_q, consumable_active_q, equipment_active_q, get_user, get_user_accessories, get_user_consumables, get_user_equipment
from assignments.models.asset_assignment import AccessoryAssignment, ConsumableIssue, EquipmentAssignment
from users.api.serializers.users import UserAccessoryAssignmentSerializer, UserConsumableIssueSerializer, UserProfileSerializer
from users.models.users import User



class UserProfileViewSet(RetrieveModelMixin, GenericViewSet):

    permission_classes = [CanViewUserProfile]
    serializer_class = UserProfileSerializer
    lookup_field = "public_id"

    def get_queryset(self):

        queryset = (
            User.objects
            .filter(is_active=True)
            .annotate(

                equipment_count=Count(
                    "equipment_assignments__equipment",
                    filter=equipment_active_q(self.request.user),
                    distinct=True,
                ),

                accessory_count=Count(
                    "accessory_assignments__accessory",
                    filter=accessory_active_q(self.request.user),
                    distinct=True,
                ),

                consumable_count=Count(
                    "consumable_assignments__consumable",
                    filter=consumable_active_q(self.request.user),
                    distinct=True,
                ),
            )
        )

        return queryset
    
class UserEquipmentViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = EquipmentSerializer
    pagination_class = FlexiblePagination

    def get_queryset(self):
        user = get_user(self.kwargs["user_public_id"])

        queryset = get_user_equipment(user)

        queryset = filter_user_assets_by_scope(
            self.request.user,
            queryset,
            "room"
        )

        return queryset

class UserAccessoryAssignmentViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = UserAccessoryAssignmentSerializer
    pagination_class = FlexiblePagination

    def get_queryset(self):
        user = get_user(self.kwargs["user_public_id"])

        queryset = get_user_accessories(user).select_related(
            "accessory",
            "accessory__room",
            "accessory__room__location",
            "accessory__room__location__department",
            "assigned_by",
        )

        queryset = filter_user_assets_by_scope(
            self.request.user,
            queryset,
            "accessory__room"
        )

        return queryset


class UserConsumableIssueViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = UserConsumableIssueSerializer
    pagination_class = FlexiblePagination

    def get_queryset(self):
        user = get_user(self.kwargs["user_public_id"])

        queryset = get_user_consumables(user).select_related(
            "consumable",
            "consumable__room",
            "consumable__room__location",
            "consumable__room__location__department",
            "assigned_by",
        ).order_by("-assigned_at")

        queryset = filter_user_assets_by_scope(
            self.request.user,
            queryset,
            "consumable__room"
        )

        return queryset

class UserAssetStatusView(APIView):
    permission_classes = [UserPermission]

    def get(self, request, user_public_id):

        user = get_object_or_404(User, public_id=user_public_id)

        equipment = EquipmentAssignment.objects.filter(
            user=user,
            returned_at__isnull=True,
            equipment__is_deleted=False,
        ).count()

        accessories = AccessoryAssignment.objects.filter(
            user=user,
            returned_at__isnull=True,
            accessory__is_deleted=False,
        ).count()

        consumables = ConsumableIssue.objects.filter(
            user=user,
            returned_at__isnull=True,
            consumable__is_deleted=False,
        ).count()

        return Response({
            "has_assets": (equipment + accessories + consumables) > 0,
            "equipment": equipment,
            "accessories": accessories,
            "consumables": consumables,
        })