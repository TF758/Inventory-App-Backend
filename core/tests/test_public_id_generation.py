import time
from concurrent.futures import ThreadPoolExecutor
from django.test import TestCase
from core.models.base import PublicIDRegistry
from assets.asset_factories import AccessoryFactory
from assets.models.assets import Accessory



class PublicIDTests(TestCase):

    # 1️⃣ ID generated on save
    def test_public_id_generated_on_save(self):
        obj = AccessoryFactory.create()

        self.assertIsNotNone(obj.public_id)
        self.assertTrue(obj.public_id.startswith("AC"))

    # 2️⃣ registry entry created
    def test_registry_entry_created_on_save(self):
        obj = AccessoryFactory.create()

        exists = PublicIDRegistry.objects.filter(
            public_id=obj.public_id
        ).exists()

        self.assertTrue(exists)

    # 3️⃣ manual public_id respected
    def test_manual_public_id_not_overwritten(self):
        obj = AccessoryFactory.build(public_id="ACMANUAL123", room=None)

        obj.save()

        self.assertEqual(obj.public_id, "ACMANUAL123")

    # 4️⃣ bulk_create generates IDs
    def test_bulk_create_generates_ids(self):
        objs = AccessoryFactory.build_batch(5, room=None)

        Accessory.objects.bulk_create(objs)

        for obj in objs:
            self.assertIsNotNone(obj.public_id)
            self.assertTrue(obj.public_id.startswith("AC"))

    # 5️⃣ registry entries created for bulk
    def test_bulk_create_registry_entries(self):
        objs = AccessoryFactory.build_batch(10, room=None)

        Accessory.objects.bulk_create(objs)

        ids = [o.public_id for o in objs]

        count = PublicIDRegistry.objects.filter(
            public_id__in=ids
        ).count()

        self.assertEqual(count, 10)

    # 6️⃣ bulk IDs unique
    def test_bulk_ids_are_unique(self):
        objs = AccessoryFactory.build_batch(30, room=None)

        Accessory.objects.bulk_create(objs)

        ids = [o.public_id for o in objs]

        self.assertEqual(len(ids), len(set(ids)))

    # 7️⃣ ID never reused after deletion
    def test_registry_prevents_reuse(self):
        obj = AccessoryFactory.create()
        old_id = obj.public_id

        obj.delete()

        new_obj = AccessoryFactory.create()

        self.assertNotEqual(new_obj.public_id, old_id)

    # 8️⃣ registry persists after object deletion
    def test_registry_persists_after_object_deleted(self):
        obj = AccessoryFactory.create()
        pid = obj.public_id

        obj.delete()

        exists = PublicIDRegistry.objects.filter(public_id=pid).exists()

        self.assertTrue(exists)

    # 9️⃣ prefix applied correctly
    def test_prefix_applied(self):
        obj = AccessoryFactory.create()

        self.assertTrue(obj.public_id.startswith("AC"))

    # 🔟 bulk_create respects existing IDs
    def test_bulk_create_respects_existing_ids(self):
        objs = AccessoryFactory.build_batch(2, room=None)

        objs[0].public_id = "ACMANUALTEST"

        Accessory.objects.bulk_create(objs)

        self.assertEqual(objs[0].public_id, "ACMANUALTEST")
        self.assertIsNotNone(objs[1].public_id)

    # 1️⃣1️⃣ bulk performance sanity check
    def test_bulk_create_reasonable_speed(self):
        objs = AccessoryFactory.build_batch(1000, room=None)

        start = time.time()

        Accessory.objects.bulk_create(objs)

        duration = time.time() - start

        self.assertLess(duration, 2)

    # 1️⃣2️⃣ concurrent ID generation safety
    def test_parallel_id_generation(self):

        def create_obj():
            obj = AccessoryFactory.create()
            return obj.public_id

        with ThreadPoolExecutor(max_workers=10) as executor:
            ids = list(executor.map(lambda _: create_obj(), range(20)))

        self.assertEqual(len(ids), len(set(ids)))