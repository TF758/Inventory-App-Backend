from django.test import TestCase

from data_import.services.equipment_importer import EquipmentImporter
from users.factories.user_factories import UserFactory
from users.models.roles import RoleAssignment
from assets.models.assets import EquipmentStatus
from sites.factories.site_factories import RoomFactory




class EquipmentImporterTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()
        cls.room = RoomFactory()

        role = RoleAssignment.objects.create(
            user=cls.user,
            role="ROOM_CLERK",
            room=cls.room,
        )

        cls.user.active_role = role
        cls.user.save()

    def test_status_is_normalized(self):

        importer = EquipmentImporter(user=self.user)

        row = {
            "name": "Laptop",
            "brand": "Dell",
            "model": "XPS",
            "serial_number": "123",
            "status": "ok",
            "room": self.room.public_id,
        }

        normalized = importer.normalize_row(row)

        self.assertEqual(normalized["status"], EquipmentStatus.OK)

    
    def test_invalid_status_defaults(self):

        importer = EquipmentImporter(user=self.user)

        row = {
            "status": "invalid"
        }

        normalized = importer.normalize_row(row)

        self.assertEqual(normalized["status"], EquipmentStatus.OK)
    

    def test_whitespace_is_trimmed(self):

        importer = EquipmentImporter(user=self.user)

        row = {
            "name": " Laptop ",
            "brand": " Dell ",
            "model": " XPS ",
            "serial_number": " 123 ",
            "status": " ok ",
            "room": self.room.public_id,
        }

        normalized = importer.normalize_row(row)

        self.assertEqual(normalized["name"], "Laptop")