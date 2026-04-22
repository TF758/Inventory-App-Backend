


from data_import.services.accessory_importer import AccessoryImporter
from data_import.services.consumable_importer import ConsumableImporter
from data_import.services.equipment_importer import EquipmentImporter


def get_asset_importer(asset_type: str, *, user, job):
    mapping = {
        "equipment": EquipmentImporter,
        "accessory": AccessoryImporter,
        "consumable": ConsumableImporter,
    }

    importer_cls = mapping.get(asset_type)

    if not importer_cls:
        raise ValueError(f"Unsupported asset type '{asset_type}'.")

    return importer_cls(user=user, job=job)