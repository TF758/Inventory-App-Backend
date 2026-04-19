

from data_import.services.base_importer import BaseAssetImporter
from assets.models.assets import Accessory, Consumable
from assets.api.serializers.consumables import ConsumableWriteSerializer


class ConsumableImporter(BaseAssetImporter):
    serializer_class = ConsumableWriteSerializer
    required_headers = {"name", "description", "quantity", "low_stock_threshold", "room"}
    allowed_headers = required_headers

    def normalize_row(self, row: dict) -> dict:
        row = super().normalize_row(row)

        try:
            row["quantity"] = int(row.get("quantity"))
        except (TypeError, ValueError):
            raise ValueError("Quantity must be an integer.")

        try:
            row["low_stock_threshold"] = int(row.get("low_stock_threshold"))
        except (TypeError, ValueError):
            raise ValueError("Low stock threshold must be an integer.")

        return row

    def build_payload(self, row: dict, room):
        return {
            "name": row.get("name", ""),
            "description": row.get("description", ""),
            "quantity": row.get("quantity"),
            "low_stock_threshold": row.get("low_stock_threshold"),
            "room": room.public_id,
        }

    def get_file_dedupe_key(self, row: dict, room):
        name = (row.get("name") or "").strip().lower()
        return (name, room.public_id)

    def exists_in_db(self, row: dict, room):
        return Consumable.objects.filter(
            name=(row.get("name") or "").strip(),
            room=room,
        ).exists()