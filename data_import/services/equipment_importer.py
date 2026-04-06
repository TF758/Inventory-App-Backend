
from db_inventory.models.assets import Equipment, EquipmentStatus
from db_inventory.serializers.equipment import EquipmentWriteSerializer

from .base_importer import BaseAssetImporter


class EquipmentImporter(BaseAssetImporter):
    asset_type = "equipment"
    serializer_class = EquipmentWriteSerializer
    required_headers = {"name", "brand", "model", "serial_number", "status", "room"}
    allowed_headers = required_headers

    def normalize_row(self, row: dict) -> dict:
        row = super().normalize_row(row)
        row["name"] = row.get("name", "")
        row["brand"] = row.get("brand", "")
        row["model"] = row.get("model", "")

        serial = row.get("serial_number", "")
        row["serial_number"] = serial or None

        status = (row.get("status") or "").strip().upper()
        valid_statuses = {choice for choice, _ in EquipmentStatus.choices}
        row["status"] = status if status in valid_statuses else EquipmentStatus.OK
        return row

    def build_serializer_payload(self, row: dict, room) -> dict:
        return {
            "name": row["name"],
            "brand": row["brand"],
            "model": row["model"],
            "serial_number": row["serial_number"],
            "room": room.public_id,
        }

    def get_dedupe_key(self, row: dict, room) -> tuple:
        return (
            row.get("name", "").strip(),
            row.get("serial_number") or "",
        )

    def is_duplicate(self, row: dict, room) -> bool:
        name = row.get("name", "").strip()
        serial = row.get("serial_number")

        if not serial:
            return False

        return Equipment.objects.filter(
            name=name,
            serial_number=serial,
        ).exists()