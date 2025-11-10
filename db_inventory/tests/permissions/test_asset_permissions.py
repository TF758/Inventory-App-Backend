from db_inventory.tests.utils._asset_permission_base import AssetPermissionTestBase
from db_inventory.factories import EquipmentFactory, AccessoryFactory, ConsumableFactory
from rest_framework.test import APIClient, APITestCase


class EquipmentPermissionTests(AssetPermissionTestBase, APITestCase):
    asset_factory = EquipmentFactory
    asset_name_singular = "equipment"
    asset_name_plural = "equipments"


class AccessoryPermissionTests(AssetPermissionTestBase, APITestCase):
    asset_factory = AccessoryFactory
    asset_name_singular = "accessory"
    asset_name_plural = "accessories"


class ConsumablePermissionTests(AssetPermissionTestBase, APITestCase):
    asset_factory = ConsumableFactory
    asset_name_singular = "consumable"
    asset_name_plural = "consumables"