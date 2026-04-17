from django.test import TestCase
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

from data_import.services.accessory_importer import AccessoryImporter
from data_import.services.consumable_importer import ConsumableImporter

from db_inventory.factories.user_factories import UserFactory
from db_inventory.models.assets import Accessory, Consumable
from db_inventory.models.roles import RoleAssignment
from sites.factories.site_factories import RoomFactory



class BaseImporterSetup(TestCase):

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

    def _create_csv(self, name, content):
        return default_storage.save(name, ContentFile(content))


# -------------------------
# Accessory Importer
# -------------------------

class AccessoryImporterTests(BaseImporterSetup):

    def test_accessory_import_happy_path(self):

        csv_content = (
            "name,serial_number,quantity,room\n"
            f"Mouse,SN1,5,{self.room.public_id}\n"
        )

        file_name = self._create_csv("accessory.csv", csv_content)

        importer = AccessoryImporter(user=self.user)

        result = importer.run(stored_file_name=file_name)

        self.assertEqual(result["summary"]["imported_rows"], 1)
        self.assertEqual(Accessory.objects.count(), 1)


# -------------------------
# Consumable Importer
# -------------------------

class ConsumableImporterTests(BaseImporterSetup):

    def test_consumable_import_happy_path(self):

        csv_content = (
            "name,description,quantity,low_stock_threshold,room\n"
            f"Paper,Printer paper,10,2,{self.room.public_id}\n"
        )

        file_name = self._create_csv("consumable.csv", csv_content)

        importer = ConsumableImporter(user=self.user)

        result = importer.run(stored_file_name=file_name)

        self.assertEqual(result["summary"]["imported_rows"], 1)
        self.assertEqual(Consumable.objects.count(), 1)