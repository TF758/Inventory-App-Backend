from django.test import TestCase
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

from data_import.services.equipment_importer import EquipmentImporter
from users.factories.user_factories import UserFactory
from users.models.roles import RoleAssignment
from sites.factories.site_factories import RoomFactory, LocationFactory, DepartmentFactory


class ImporterPermissionTests(TestCase):

    @classmethod
    def setUpTestData(cls):

        cls.user = UserFactory()

        cls.department = DepartmentFactory()
        cls.location = LocationFactory(department=cls.department)

        cls.room_a = RoomFactory(location=cls.location)
        cls.room_b = RoomFactory(location=cls.location)

        cls.other_department = DepartmentFactory()
        cls.other_location = LocationFactory(department=cls.other_department)
        cls.other_room = RoomFactory(location=cls.other_location)

    def _create_csv(self, content):

        return default_storage.save(
            "permission_test.csv",
            ContentFile(content),
        )

    def _run_import(self, user, room):

        csv_content = (
            "name,brand,model,serial_number,status,room\n"
            f"Laptop,Dell,XPS,123,OK,{room.public_id}\n"
        )

        file_name = self._create_csv(csv_content)

        importer = EquipmentImporter(user=user)

        return importer.run(stored_file_name=file_name)

    # -----------------------------
    # Viewer role
    # -----------------------------

    def test_viewer_role_cannot_import(self):

        role = RoleAssignment.objects.create(
            user=self.user,
            role="ROOM_VIEWER",
            room=self.room_a,
        )

        self.user.active_role = role
        self.user.save()

        result = self._run_import(self.user, self.room_a)

        self.assertEqual(result["summary"]["imported_rows"], 0)
        self.assertEqual(result["summary"]["skipped_rows"], 1)

    # -----------------------------
    # Clerk role
    # -----------------------------

    def test_clerk_role_cannot_import(self):

        role = RoleAssignment.objects.create(
            user=self.user,
            role="ROOM_CLERK",
            room=self.room_a,
        )

        self.user.active_role = role
        self.user.save()

        result = self._run_import(self.user, self.room_a)

        self.assertEqual(result["summary"]["imported_rows"], 0)
        self.assertEqual(result["summary"]["skipped_rows"], 1)

    # -----------------------------
    # Room admin
    # -----------------------------

    def test_room_admin_can_import_own_room(self):

        role = RoleAssignment.objects.create(
            user=self.user,
            role="ROOM_ADMIN",
            room=self.room_a,
        )

        self.user.active_role = role
        self.user.save()

        result = self._run_import(self.user, self.room_a)

        self.assertEqual(result["summary"]["imported_rows"], 1)

    def test_room_admin_cannot_import_other_room(self):

        role = RoleAssignment.objects.create(
            user=self.user,
            role="ROOM_ADMIN",
            room=self.room_a,
        )

        self.user.active_role = role
        self.user.save()

        result = self._run_import(self.user, self.room_b)

        self.assertEqual(result["summary"]["imported_rows"], 0)
        self.assertEqual(result["summary"]["skipped_rows"], 1)

    # -----------------------------
    # Location admin
    # -----------------------------

    def test_location_admin_can_import_rooms_in_location(self):

        role = RoleAssignment.objects.create(
            user=self.user,
            role="LOCATION_ADMIN",
            location=self.location,
        )

        self.user.active_role = role
        self.user.save()

        result = self._run_import(self.user, self.room_a)

        self.assertEqual(result["summary"]["imported_rows"], 1)

    def test_location_admin_cannot_import_other_location(self):

        role = RoleAssignment.objects.create(
            user=self.user,
            role="LOCATION_ADMIN",
            location=self.location,
        )

        self.user.active_role = role
        self.user.save()

        result = self._run_import(self.user, self.other_room)

        self.assertEqual(result["summary"]["imported_rows"], 0)
        self.assertEqual(result["summary"]["skipped_rows"], 1)

    # -----------------------------
    # Department admin
    # -----------------------------

    def test_department_admin_can_import_department_rooms(self):

        role = RoleAssignment.objects.create(
            user=self.user,
            role="DEPARTMENT_ADMIN",
            department=self.department,
        )

        self.user.active_role = role
        self.user.save()

        result = self._run_import(self.user, self.room_a)

        self.assertEqual(result["summary"]["imported_rows"], 1)

    def test_department_admin_cannot_import_other_department(self):

        role = RoleAssignment.objects.create(
            user=self.user,
            role="DEPARTMENT_ADMIN",
            department=self.department,
        )

        self.user.active_role = role
        self.user.save()

        result = self._run_import(self.user, self.other_room)

        self.assertEqual(result["summary"]["imported_rows"], 0)
        self.assertEqual(result["summary"]["skipped_rows"], 1)

    # -----------------------------
    # Site admin
    # -----------------------------

    def test_site_admin_can_import_any_room(self):

        role = RoleAssignment.objects.create(
            user=self.user,
            role="SITE_ADMIN",
        )

        self.user.active_role = role
        self.user.save()

        result = self._run_import(self.user, self.other_room)

        self.assertEqual(result["summary"]["imported_rows"], 1)