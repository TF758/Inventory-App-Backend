
from db_inventory.models.assets import Accessory
from db_inventory.serializers.accessories import AccessoryWriteSerializer

from .base_importer import BaseAssetImporter


class AccessoryImporter(BaseAssetImporter):
    asset_type = "accessory"
    serializer_class = AccessoryWriteSerializer
    required_headers = {"name", "serial_number", "quantity", "room"}
    allowed_headers = required_headers

    def normalize_row(self, row: dict) -> dict:
        row = super().normalize_row(row)
        row["name"] = row.get("name", "")
        row["serial_number"] = row.get("serial_number") or None

        quantity = row.get("quantity", "")
        if quantity == "":
            raise ValueError("Quantity is required.")
        try:
            row["quantity"] = int(quantity)
        except (TypeError, ValueError):
            raise ValueError("Quantity must be an integer.")

        return row

    def build_serializer_payload(self, row: dict, room) -> dict:
        return {
            "name": row["name"],
            "serial_number": row["serial_number"],
            "quantity": row["quantity"],
            "room": room.public_id,
        }

    def get_dedupe_key(self, row: dict, room) -> tuple:
        return (
            row.get("name", "").strip(),
            row.get("serial_number") or "",
            room.public_id,
        )

    def is_duplicate(self, row: dict, room) -> bool:
        name = row.get("name", "").strip()
        serial = row.get("serial_number")

        qs = Accessory.objects.filter(name=name, room=room)
        if serial:
            qs = qs.filter(serial_number=serial)
        else:
            qs = qs.filter(serial_number__isnull=True)

        return qs.exists()