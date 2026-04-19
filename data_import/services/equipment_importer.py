


from data_import.services.base_importer import BaseAssetImporter
from assets.models.assets import Equipment, EquipmentStatus
from assets.api.serializers.equipment import EquipmentWriteSerializer


class EquipmentImporter(BaseAssetImporter):
    serializer_class = EquipmentWriteSerializer
    required_headers = {"name", "brand", "model", "serial_number", "status", "room"}
    allowed_headers = required_headers

    def normalize_row(self, row: dict) -> dict:
        row = super().normalize_row(row)

        serial = row.get("serial_number") or None
        row["serial_number"] = serial

        status = (row.get("status") or "").strip().upper()
        valid_statuses = {choice for choice, _ in EquipmentStatus.choices}
        row["status"] = status if status in valid_statuses else EquipmentStatus.OK

        return row

    def build_payload(self, row: dict, room):
        return {
            "name": row.get("name", ""),
            "brand": row.get("brand", ""),
            "model": row.get("model", ""),
            "serial_number": row.get("serial_number"),
            "status": row.get("status"),
            "room": room.public_id,
        }

    def get_file_dedupe_key(self, row: dict, room):
        name = (row.get("name") or "").strip().lower()
        serial = (row.get("serial_number") or "").strip().lower()

        return ( name, serial)
    def exists_in_db(self, row: dict, room):
        return Equipment.objects.filter(
            name=(row.get("name") or "").strip(),
            serial_number=row.get("serial_number"),
        ).exists()