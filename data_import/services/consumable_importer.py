

from db_inventory.models.assets import Consumable
from db_inventory.serializers.consumables import ConsumableWriteSerializer

from .base_importer import BaseAssetImporter


class ConsumableImporter(BaseAssetImporter):
    asset_type = "consumable"
    serializer_class = ConsumableWriteSerializer
    required_headers = {"name", "description", "quantity", "low_stock_threshold", "room"}
    allowed_headers = required_headers

    def normalize_row(self, row: dict) -> dict:
        row = super().normalize_row(row)
        row["name"] = row.get("name", "")
        row["description"] = row.get("description", "")

        quantity = row.get("quantity", "")
        threshold = row.get("low_stock_threshold", "")

        if quantity == "":
            raise ValueError("Quantity is required.")
        if threshold == "":
            raise ValueError("Low stock threshold is required.")

        try:
            row["quantity"] = int(quantity)
        except (TypeError, ValueError):
            raise ValueError("Quantity must be an integer.")

        try:
            row["low_stock_threshold"] = int(threshold)
        except (TypeError, ValueError):
            raise ValueError("Low stock threshold must be an integer.")

        return row

    def build_serializer_payload(self, row: dict, room) -> dict:
        return {
            "name": row["name"],
            "description": row["description"],
            "quantity": row["quantity"],
            "low_stock_threshold": row["low_stock_threshold"],
            "room": room.public_id,
        }

    def get_dedupe_key(self, row: dict, room) -> tuple:
        return (
            row.get("name", "").strip(),
            room.public_id,
        )

    def is_duplicate(self, row: dict, room) -> bool:
        return Consumable.objects.filter(
            name=row.get("name", "").strip(),
            room=room,
        ).exists()