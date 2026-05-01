from django.test import TestCase
from core.permissions.helpers import filter_queryset_by_scope
from assets.asset_factories import AccessoryFactory, ConsumableFactory, EquipmentFactory
from assets.models.assets import Equipment
from users.factories.user_factories import UserFactory
from users.models.roles import RoleAssignment
from sites.factories.site_factories import DepartmentFactory, LocationFactory, RoomFactory



class FilterQuerysetByScopeTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        # Structure
        cls.dept = DepartmentFactory()
        cls.other_dept = DepartmentFactory()

        cls.loc = LocationFactory(department=cls.dept)
        cls.other_loc = LocationFactory(department=cls.other_dept)

        cls.room = RoomFactory(location=cls.loc)
        cls.other_room = RoomFactory(location=cls.other_loc)

        # User
        cls.user = UserFactory()

        # Assets
        cls.equipment_in_scope = EquipmentFactory(room=cls.room)
        cls.equipment_out_scope = EquipmentFactory(room=cls.other_room)

        cls.accessory_in_scope = AccessoryFactory(room=cls.room)
        cls.accessory_out_scope = AccessoryFactory(room=cls.other_room)

        cls.consumable_in_scope = ConsumableFactory(room=cls.room)
        cls.consumable_out_scope = ConsumableFactory(room=cls.other_room)

    # -------------------------
    # Room-level scope
    # -------------------------

    def test_room_scope_filters_correctly_equipment(self):
        role = RoleAssignment.objects.create(
            user=self.user,
            role="ROOM_ADMIN",
            room=self.room,
        )
        self.user.active_role = role
        self.user.save()

        qs = EquipmentFactory._meta.model.objects.all()

        filtered = filter_queryset_by_scope(self.user, qs, qs.model)

        self.assertIn(self.equipment_in_scope, filtered)
        self.assertNotIn(self.equipment_out_scope, filtered)

    def test_room_scope_filters_accessory(self):
        role = RoleAssignment.objects.create(
            user=self.user,
            role="ROOM_ADMIN",
            room=self.room,
        )
        self.user.active_role = role
        self.user.save()

        qs = AccessoryFactory._meta.model.objects.all()

        filtered = filter_queryset_by_scope(self.user, qs, qs.model)

        self.assertIn(self.accessory_in_scope, filtered)
        self.assertNotIn(self.accessory_out_scope, filtered)

    def test_room_scope_filters_consumable(self):
        role = RoleAssignment.objects.create(
            user=self.user,
            role="ROOM_ADMIN",
            room=self.room,
        )
        self.user.active_role = role
        self.user.save()

        qs = ConsumableFactory._meta.model.objects.all()

        filtered = filter_queryset_by_scope(self.user, qs, qs.model)

        self.assertIn(self.consumable_in_scope, filtered)
        self.assertNotIn(self.consumable_out_scope, filtered)

    # -------------------------
    # Location-level scope
    # -------------------------

    def test_location_scope_includes_all_rooms(self):
        role = RoleAssignment.objects.create(
            user=self.user,
            role="LOCATION_ADMIN",
            location=self.loc,
        )
        self.user.active_role = role
        self.user.save()

        qs = EquipmentFactory._meta.model.objects.all()

        filtered = filter_queryset_by_scope(self.user, qs, qs.model)

        self.assertIn(self.equipment_in_scope, filtered)
        self.assertNotIn(self.equipment_out_scope, filtered)

    # -------------------------
    # Department-level scope
    # -------------------------

    def test_department_scope_includes_all_locations(self):
        role = RoleAssignment.objects.create(
            user=self.user,
            role="DEPARTMENT_ADMIN",
            department=self.dept,
        )
        self.user.active_role = role
        self.user.save()

        qs = EquipmentFactory._meta.model.objects.all()

        filtered = filter_queryset_by_scope(self.user, qs, qs.model)

        self.assertIn(self.equipment_in_scope, filtered)
        self.assertNotIn(self.equipment_out_scope, filtered)

    # -------------------------
    # Site admin bypass
    # -------------------------

    def test_site_admin_sees_all(self):
        role = RoleAssignment.objects.create(
            user=self.user,
            role="SITE_ADMIN",
        )
        self.user.active_role = role
        self.user.save()

        qs = EquipmentFactory._meta.model.objects.all()

        filtered = filter_queryset_by_scope(self.user, qs, qs.model)

        self.assertIn(self.equipment_in_scope, filtered)
        self.assertIn(self.equipment_out_scope, filtered)

    # -------------------------
    # No role assigned
    # -------------------------

    def test_no_role_returns_empty_queryset(self):
        qs = EquipmentFactory._meta.model.objects.all()

        filtered = filter_queryset_by_scope(self.user, qs, qs.model)

        self.assertEqual(filtered.count(), 0)

    # -------------------------
    # Defensive: invalid model
    # -------------------------

    def test_unknown_model_returns_empty(self):
        qs = Equipment.objects.none()

        filtered = filter_queryset_by_scope(self.user, qs, qs.model)

        self.assertEqual(filtered.count(), 0)