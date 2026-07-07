from rest_framework.test import APITestCase
from django.urls import reverse

from access.models import Permission, RolePermission
from users.models.roles import RoleAssignment
from users.factories.user_factories import UserFactory
from sites.factories.site_factories import (
    DepartmentFactory,
    LocationFactory,
    RoomFactory,
)


ASSIGNMENT_OPERATION_PERMISSIONS = (
    # Current permission model
    "assignments.view",
    "assignments.create",
    "assignments.update",
    "assignments.unassign",
    "assignments.reassign",
    "assignments.restock",

    # Legacy / transitional assignment endpoint names.
    # Keep these while older APIViews are being normalized to
    # required_permission = "assignments.create".
    "assignments.assign",
    "assignments.issue",
    "assignments.return",

    # Asset capability checks used by assignment-style flows.
    "assets.view",
    "assets.assign",
    "assets.unassign",
    "assets.update",
    "assets.use",
    "assets.restock",
    "assets.update_status",
    "assets.change_status",
)

CONDEMN_OPERATION_PERMISSIONS = (
    "assets.condemn",
)

ASSIGNMENT_TEST_ROLES = (
    "ROOM_ADMIN",
    "LOCATION_ADMIN",
)


PERMISSION_SCOPE_BY_DOMAIN = {
    "assignments": "ROOM",
    "assets": "ROOM",
    "returns": "ROOM",
}


def permission_defaults(code: str) -> dict:
    domain = code.split(".", 1)[0]

    return {
        "name": code.replace(".", " ").replace("_", " ").title(),
        "description": f"Test permission for {code}.",
        "domain": domain,
        "scope_type": PERMISSION_SCOPE_BY_DOMAIN.get(domain, "ROOM"),
        "sort_order": 0,
        "is_configurable": True,
    }


def ensure_permission(code: str) -> Permission:
    permission, created = Permission.objects.get_or_create(
        code=code,
        defaults=permission_defaults(code),
    )

    # Keep older fixture-created permissions usable if they were created
    # before required metadata/defaults were added to the permission model.
    changed_fields = []
    defaults = permission_defaults(code)

    for field, value in defaults.items():
        if getattr(permission, field, None) in (None, ""):
            setattr(permission, field, value)
            changed_fields.append(field)

    if changed_fields:
        permission.save(update_fields=changed_fields)

    return permission


def normalize_role_code(role):
    if hasattr(role, "role"):
        return role.role

    return role


def grant_role_permissions(role, codes):
    role_code = normalize_role_code(role)

    for code in codes:
        permission = ensure_permission(code)

        RolePermission.objects.get_or_create(
            role=role_code,
            permission=permission,
        )


def grant_assignment_operation_permissions() -> None:
    for role_code in ASSIGNMENT_TEST_ROLES:
        grant_role_permissions(
            role_code,
            ASSIGNMENT_OPERATION_PERMISSIONS,
        )


def grant_condemn_operation_permissions() -> None:
    for role_code in ASSIGNMENT_TEST_ROLES:
        grant_role_permissions(
            role_code,
            CONDEMN_OPERATION_PERMISSIONS,
        )


def create_active_room_admin(user, room):
    role = RoleAssignment.objects.create(
        user=user,
        role="ROOM_ADMIN",
        room=room,
    )

    user.active_role = role
    user.save(update_fields=["active_role"])

    return role


class AccessoryAssignmentTestBase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.department = DepartmentFactory()
        cls.location = LocationFactory(department=cls.department)
        cls.room = RoomFactory(location=cls.location)

        cls.admin = UserFactory()
        cls.admin_role = create_active_room_admin(cls.admin, cls.room)

        grant_assignment_operation_permissions()

        cls.assign_url = reverse("assign-accessory")
        cls.return_url = reverse("return-accessory")

    def authenticate_admin(self):
        self.client.force_authenticate(user=self.admin)


class CondemnAccessoryTestBase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.department = DepartmentFactory()
        cls.location = LocationFactory(department=cls.department)
        cls.room = RoomFactory(location=cls.location)

        cls.admin = UserFactory()
        cls.admin_role = create_active_room_admin(cls.admin, cls.room)

        grant_condemn_operation_permissions()

        cls.condemn_url = reverse("condemn-accessory")

    def authenticate_admin(self):
        self.client.force_authenticate(user=self.admin)


class ConsumableAPITestBase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.department = DepartmentFactory()
        cls.location = LocationFactory(department=cls.department)
        cls.room = RoomFactory(location=cls.location)

        cls.admin = UserFactory()
        cls.admin_role = create_active_room_admin(cls.admin, cls.room)

        grant_assignment_operation_permissions()

        cls.issue_url = reverse("issue-consumable")
        cls.use_url = reverse("use-consumable")
        cls.return_url = reverse("return-consumable")
        cls.report_loss_url = reverse("report-consumable-loss")

    def authenticate_admin(self):
        self.client.force_authenticate(user=self.admin)


class EquipmentAssignmentAPITestBase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.department = DepartmentFactory()
        cls.location = LocationFactory(department=cls.department)
        cls.room = RoomFactory(location=cls.location)

        cls.admin = UserFactory()
        cls.admin_role = create_active_room_admin(cls.admin, cls.room)

        grant_assignment_operation_permissions()

        cls.assign_url = reverse("assign-equipment")
        cls.unassign_url = reverse("unassign-equipment")
        cls.reassign_url = reverse("reassign-equipment")

    def authenticate_admin(self):
        self.client.force_authenticate(user=self.admin)
