from django.test import TestCase
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

from data_import.services.equipment_importer import EquipmentImporter
from db_inventory.factories.asset_factories import EquipmentFactory

from users.factories.user_factories import UserFactory
from users.models.roles import RoleAssignment
from sites.factories.site_factories import RoomFactory



class BaseImporterTests(TestCase):

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
        """Helper to write csv test file"""
        return default_storage.save(name, ContentFile(content))

    def test_import_single_equipment_row(self):

        csv_content = (
            "name,brand,model,serial_number,status,room\n"
            f"Laptop,Dell,XPS,123,OK,{self.room.public_id}\n"
        )

        file_name = self._create_csv("equipment_import.csv", csv_content)

        importer = EquipmentImporter(user=self.user)

        result = importer.run(stored_file_name=file_name)

        self.assertEqual(result["summary"]["imported_rows"], 1)

    def test_duplicate_rows_in_file(self):

        csv_content = (
            "name,brand,model,serial_number,status,room\n"
            f"Laptop,Dell,XPS,123,OK,{self.room.public_id}\n"
            f"Laptop,Dell,XPS,123,OK,{self.room.public_id}\n"
        )

        file_name = self._create_csv("dup.csv", csv_content)

        importer = EquipmentImporter(user=self.user)

        result = importer.run(stored_file_name=file_name)

        self.assertEqual(result["summary"]["imported_rows"], 1)
        self.assertEqual(result["summary"]["skipped_rows"], 1)

    def test_duplicate_in_database(self):

        EquipmentFactory(
            name="Laptop",
            serial_number="123",
            room=self.room,
        )

        csv_content = (
            "name,brand,model,serial_number,status,room\n"
            f"Laptop,Dell,XPS,123,OK,{self.room.public_id}\n"
        )

        file_name = self._create_csv("dup_db.csv", csv_content)

        importer = EquipmentImporter(user=self.user)

        result = importer.run(stored_file_name=file_name)

        self.assertEqual(result["summary"]["imported_rows"], 0)
        self.assertEqual(result["summary"]["skipped_rows"], 1)

    def test_missing_required_header(self):

        csv_content = (
            "name,brand,model,status,room\n"
            "Laptop,Dell,XPS,OK,R001\n"
        )

        file_name = self._create_csv("bad.csv", csv_content)

        importer = EquipmentImporter(user=self.user)

        with self.assertRaises(ValueError):
            importer.run(stored_file_name=file_name)

    def test_user_without_active_role_cannot_import(self):

        self.user.active_role = None
        self.user.save()

        csv_content = (
            "name,brand,model,serial_number,status,room\n"
            f"Laptop,Dell,XPS,123,OK,{self.room.public_id}\n"
        )

        file_name = self._create_csv("perm.csv", csv_content)

        importer = EquipmentImporter(user=self.user)

        result = importer.run(stored_file_name=file_name)

        self.assertEqual(result["summary"]["skipped_rows"], 1)
    

    def test_invalid_row_data_fails(self):

        csv_content = (
            "name,brand,model,serial_number,status,room\n"
            f",Dell,XPS,123,OK,{self.room.public_id}\n"
        )

        file_name = self._create_csv("invalid.csv", csv_content)

        importer = EquipmentImporter(user=self.user)

        result = importer.run(stored_file_name=file_name)

        self.assertEqual(result["summary"]["failed_rows"], 1)


    def test_room_does_not_exist(self):

        csv_content = (
            "name,brand,model,serial_number,status,room\n"
            "Laptop,Dell,XPS,123,OK,INVALIDROOM\n"
        )

        file_name = self._create_csv("invalid_room.csv", csv_content)

        importer = EquipmentImporter(user=self.user)

        result = importer.run(stored_file_name=file_name)

        self.assertEqual(result["summary"]["failed_rows"], 1)

    
    def test_csv_row_limit_exceeded(self):

        rows = "\n".join(
            f"Laptop{i},Dell,XPS,{i},OK,{self.room.public_id}"
            for i in range(10001)
        )

        csv_content = "name,brand,model,serial_number,status,room\n" + rows

        file_name = self._create_csv("large.csv", csv_content)

        importer = EquipmentImporter(user=self.user)

        with self.assertRaises(ValueError):
            importer.run(stored_file_name=file_name)
    

    def test_blank_rows_are_ignored(self):

        csv_content = (
            "name,brand,model,serial_number,status,room\n"
            f"Laptop,Dell,XPS,123,OK,{self.room.public_id}\n"
            ",,,,,\n"
        )

        file_name = self._create_csv("blank_rows.csv", csv_content)

        importer = EquipmentImporter(user=self.user)

        result = importer.run(stored_file_name=file_name)

        self.assertEqual(result["summary"]["imported_rows"], 1)