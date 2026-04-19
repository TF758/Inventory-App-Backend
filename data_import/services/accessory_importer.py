

from data_import.services.base_importer import BaseAssetImporter
from assets.models.assets import Accessory
from assets.api.serializers.accessories import AccessoryWriteSerializer


class AccessoryImporter(BaseAssetImporter):
    serializer_class = AccessoryWriteSerializer
    required_headers = {"name", "serial_number", "quantity", "room"}
    allowed_headers = required_headers

    def normalize_row(self, row: dict) -> dict:
        row = super().normalize_row(row)

        serial = row.get("serial_number") or None
        row["serial_number"] = serial

        try:
            row["quantity"] = int(row.get("quantity"))
        except (TypeError, ValueError):
            raise ValueError("Quantity must be an integer.")

        return row

    def build_payload(self, row: dict, room):
        return {
            "name": row.get("name", ""),
            "serial_number": row.get("serial_number"),
            "quantity": row.get("quantity"),
            "room": room.public_id,
        }

    def get_file_dedupe_key(self, row: dict, room):
        name = (row.get("name") or "").strip().lower()
        serial = (row.get("serial_number") or "").strip().lower()

        return ( name, serial, room.public_id, )
    
    def exists_in_db(self, row: dict, room):
        return Accessory.objects.filter(
            name=(row.get("name") or "").strip(),
            serial_number=row.get("serial_number"),
        ).exists()