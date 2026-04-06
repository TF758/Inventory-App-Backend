

from data_import.models import ImportJob
from data_import.services.accessory_importer import AccessoryImporter
from data_import.services.consumable_importer import ConsumableImporter
from data_import.services.equipment_importer import EquipmentImporter


def get_importer(job: ImportJob):
    if job.asset_type == ImportJob.AssetType.EQUIPMENT:
        return EquipmentImporter(job=job)
    if job.asset_type == ImportJob.AssetType.ACCESSORY:
        return AccessoryImporter(job=job)
    if job.asset_type == ImportJob.AssetType.CONSUMABLE:
        return ConsumableImporter(job=job)
    raise ValueError(f"Unsupported asset type: {job.asset_type}")