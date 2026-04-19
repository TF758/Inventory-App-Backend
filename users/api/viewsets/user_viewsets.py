from django.shortcuts import get_object_or_404
from rest_framework import viewsets
from rest_framework import mixins
from rest_framework import status, views
from django.db import transaction
from core.models.audit import AuditLog
from assets.api.serializers.equipment import EquipmentSerializer
from users.models.roles import RoleAssignment
from users.models.users import User
from users.api.serializers.roles import RoleWriteSerializer
from users.api.serializers.users import UserAccessoryAssignmentSerializer, UserAreaSerializer, UserConsumableIssueSerializer, UserPlacementWriteSerializer, UserProfileSerializer, UserReadSerializerFull, UserTransferSerializer, UserWriteSerializer
from sites.models.sites import UserPlacement, Room, Department, Location
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter
from core.filters import  UserFilter, UserPlacementFilter
from core.mixins import NotificationMixin, ScopeFilterMixin
from core.pagination import FlexiblePagination
from core.permissions import UserPermission,  UserPlacementPermission, filter_queryset_by_scope, FullUserCreatePermission
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.exceptions import PermissionDenied
from core.mixins import AuditMixin
from core.permissions.helpers import ensure_permission, filter_user_assets_by_scope
from django.db.models import Count
from rest_framework.viewsets import GenericViewSet
from rest_framework.mixins import RetrieveModelMixin
from django.utils import timezone
from core.permissions.users import CanViewUserProfile
from core.models.notifications import Notification
from core.utils.viewset_helpers import unallocated_users_queryset
from rest_framework import viewsets
from rest_framework.response import Response
from core.utils.query_helpers import accessory_active_q, consumable_active_q, equipment_active_q, get_user, get_user_accessories, get_user_consumables, get_user_equipment
from assignments.models.asset_assignment import AccessoryAssignment, ConsumableIssue, EquipmentAssignment
from assets.services.assets import user_has_active_assets


class UserModelViewSet(AuditMixin, ScopeFilterMixin, viewsets.ModelViewSet):
    """
    User directory + self-service profile updates.

    - Read users
    - Users may update themselves
    - No user creation
    - No admin actions
    """

    queryset = User.objects.all().order_by("-id")
    serializer_class = UserReadSerializerFull
    lookup_field = "public_id"

    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ["^email", "email"]
    filterset_class = UserFilter
    pagination_class = FlexiblePagination

    permission_classes = [UserPermission]
    http_method_names = ["get", "put", "patch", "head", "options"]

    def get_serializer_class(self):
        if self.action in ["update", "partial_update"]:
            return UserWriteSerializer
        return UserReadSerializerFull

    def get_queryset(self):
        user = self.request.user
        active_role = getattr(user, "active_role", None)

        qs = User.objects.all().order_by("-id")

        if self.action == "list" and active_role:
            qs = filter_queryset_by_scope(user, qs, User)

        return qs


class UserPlacementViewSet(AuditMixin, NotificationMixin,viewsets.ModelViewSet):

    queryset = UserPlacement.objects.select_related(
        "user", "room", "room__location", "room__location__department"
    ).order_by("-date_joined", "-id")

    lookup_field = "public_id"
    permission_classes = [UserPlacementPermission]
    filter_backends = [DjangoFilterBackend]
    filterset_class = UserPlacementFilter

    def get_queryset(self):
        if self.action == "list":
            return filter_queryset_by_scope(
                self.request.user,
                super().get_queryset(),
                UserPlacement
            )
        return super().get_queryset()

    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return UserPlacementWriteSerializer
        return UserAreaSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user"]
        room = serializer.validated_data.get("room")

        with transaction.atomic():
            new_location = serializer.save()

            self.audit(
                event_type=AuditLog.Events.USER_ASSIGNED,
                target=new_location,
                description=f"User assigned to room {room.name if room else 'None'}",
                metadata={
                    "user_id": user.public_id,
                    "room_id": room.public_id if room else None,
                    "room_name": room.name if room else None,
                },
            )

            self.notify(
                recipient=user,
                notif_type=Notification.NotificationType.SYSTEM,
                level=Notification.Level.INFO,
                title="Room Assignment",
                message=(
                    f"You have been assigned to {room.name}"
                    if room
                    else "You have been unassigned from a room"
                ),
                entity=new_location,
                actor=request.user,
                meta={
                    "room_id": room.public_id if room else None,
                    "room_name": room.name if room else None,
                },
            )

        read_serializer = UserAreaSerializer(
            new_location,
            context=self.get_serializer_context()
        )

        return Response(read_serializer.data, status=status.HTTP_201_CREATED)

class UserTransferViewSet(AuditMixin,NotificationMixin,GenericViewSet):

    serializer_class = UserTransferSerializer
    permission_classes = [UserPlacementPermission]

    def create(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user"]
        new_room = serializer.validated_data["room"]

        with transaction.atomic():

            old_location = UserPlacement.objects.filter(
                user=user,
                is_current=True
            ).select_related("room").first()

            old_room = old_location.room if old_location else None

            if old_location:
                old_location.is_current = False
                old_location.save(update_fields=["is_current"])

            new_location = UserPlacement.objects.create(
                user=user,
                room=new_room,
                is_current=True,
                date_joined=timezone.now()
            )

            if not old_location:
                raise serializers.ValidationError(
                    {"user_id": "User has no active location to transfer from."}
                )

            if old_room and old_room == new_room:
                raise serializers.ValidationError(
                    {"room_id": "User is already assigned to this room."}
                )
            
            if user_has_active_assets(user):
                raise serializers.ValidationError({
                    "detail": (
                        "User has assigned assets. "
                        "Please return or unassign assets before transferring."
                    )
                })

            # -------------------
            # AUDIT
            # -------------------
            self.audit(
                event_type=AuditLog.Events.USER_MOVED,
                target=new_location,
                description=(
                    f"User transferred from "
                    f"{old_room.name if old_room else 'None'} "
                    f"to {new_room.name}"
                ),
                metadata={
                    "user_id": user.public_id,
                    "from_room_id": old_room.public_id if old_room else None,
                    "from_room_name": old_room.name if old_room else None,
                    "to_room_id": new_room.public_id,
                    "to_room_name": new_room.name,
                },
            )

            # -------------------
            # NOTIFY USER
            # -------------------
            self.notify(
                recipient=user,
                notif_type=Notification.NotificationType.SYSTEM,  # or define USER_MOVED
                title="Room Transfer",
                message=f"You have been moved to {new_room.name}",
                entity=new_location,
                actor=request.user,
                meta={
                    "from_room": old_room.name if old_room else None,
                    "to_room": new_room.name,
                },
            )

        read_serializer = UserAreaSerializer(
            new_location,
            context={"request": request}
        )

        return Response(read_serializer.data, status=status.HTTP_201_CREATED)
    

class UserPlacementByUserView(APIView):
    """
    Retrieve the current location assignment of a user
    by the user's public_id.
    """

    permission_classes = [UserPlacementPermission]

    def get(self, request, user_public_id: str):
        assignment = (
            UserPlacement.objects.select_related(
                "user",
                "room",
                "room__location",
                "room__location__department",
            )
            .filter(user__public_id=user_public_id, is_current=True)
            .first()
        )

        if not assignment:
            return Response(
                {"detail": "User has no current location assignment"},
                status=status.HTTP_404_NOT_FOUND,
            )
        self.check_object_permissions(request, assignment)

        serializer = UserAreaSerializer(
            assignment,
            context={"request": request},
        )
        return Response(serializer.data, status=status.HTTP_200_OK)
        


class UnallocatedUserViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = UserReadSerializerFull
    permission_classes = [UserPermission]
    pagination_class = FlexiblePagination
    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['^email', 'email']
    filterset_class = UserFilter

    def get_queryset(self):
            active_role = getattr(self.request.user, "active_role", None)

            if not active_role or active_role.role != "SITE_ADMIN":
                return User.objects.none()

            return unallocated_users_queryset()


class FullUserCreateView(AuditMixin,views.APIView):
    """
    Create a User, assign a UserPlacement, and assign a Role atomically.
    This endpoint enforces:
      - SITE_ADMIN: can create users anywhere
      - DEPARTMENT_ADMIN: can create users only inside their department
      - LOCATION_ADMIN: cannot use this endpoint
      - ROOM_ADMIN: cannot use this endpoint
    """

    permission_classes = [FullUserCreatePermission]

    def post(self, request, *args, **kwargs):
        payload = request.data
        user_data = payload.get("user", {})
        user_location_public_id = payload.get("user_location")
        role_data = payload.get("role", {})

        user_location_instance = None

        with transaction.atomic():

            # 1️⃣ Create User
            user_serializer = UserWriteSerializer(data=user_data)
            user_serializer.is_valid(raise_exception=True)
            user = user_serializer.save()

            # 2️⃣ Assign UserPlacement (permission enforced here)
            if user_location_public_id:
                ul_serializer = UserPlacementWriteSerializer(
                    data={
                        "user_id": user.public_id,
                        "room_id": user_location_public_id,
                    },
                    context={"request": request},
                )
                ul_serializer.is_valid(raise_exception=True)

                temp_ul = UserPlacement(
                    user=user,
                    room=ul_serializer.validated_data["room"]
                )

                if not UserPlacementPermission().has_object_permission(
                    request, self, temp_ul
                ):
                    raise PermissionDenied(
                        "You do not have permission to assign this location."
                    )

                user_location_instance = ul_serializer.save()

            # 3️⃣ Assign Role (permission enforced here)
            role_name = role_data.get("role")

            def resolve(model, public_id):
                if not public_id:
                    return None
                return model.objects.get(public_id=public_id)

            department = resolve(Department, role_data.get("department"))
            location = resolve(Location, role_data.get("location"))
            room = resolve(Room, role_data.get("room"))

            # Normalize scope based on role level
            if role_name.startswith("ROOM_"):
                department = None
                location = None
            elif role_name.startswith("LOCATION_"):
                department = None
                room = None
            elif role_name.startswith("DEPARTMENT_"):
                location = None
                room = None

            temp_role = RoleAssignment(
                user=user,
                role=role_name,
                department=department,
                location=location,
                room=room,
            )

            
            try:
                ensure_permission(
                    request.user,
                    role_name,
                    room=room,
                    location=location,
                    department=department,
                )
            except PermissionDenied:
                raise PermissionDenied("You do not have permission to assign this role.")

            role_serializer = RoleWriteSerializer(
                data={
                    "user": user.public_id,
                    "role": role_name,
                    "department": department.public_id if department else None,
                    "location": location.public_id if location else None,
                    "room": room.public_id if room else None,
                },
                context={"request": request},
            )
            role_serializer.is_valid(raise_exception=True)
            role_assignment = role_serializer.save()

        return Response(
            {
                "user": UserWriteSerializer(user).data,
                "user_location": (
                    UserPlacementWriteSerializer(user_location_instance).data
                    if user_location_instance else None
                ),
                "role_assignment": RoleWriteSerializer(role_assignment).data,
            },
            status=status.HTTP_201_CREATED,
        )



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