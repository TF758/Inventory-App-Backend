import time
from concurrent.futures import ThreadPoolExecutor
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.db import connection
from assets.asset_factories import AccessoryFactory
from assets.models.assets import Accessory




class PublicIDStressTests(TestCase):

    def test_bulk_create_large_dataset(self):
        objs = AccessoryFactory.build_batch(5000, room=None)

        Accessory.objects.bulk_create(objs)

        ids = [o.public_id for o in objs]

        self.assertEqual(len(ids), len(set(ids)))

    def test_registry_handles_large_volume(self):
        objs = AccessoryFactory.build_batch(2000, room=None)
        Accessory.objects.bulk_create(objs)

        new_objs = AccessoryFactory.build_batch(2000, room=None)
        Accessory.objects.bulk_create(new_objs)

        ids = [o.public_id for o in objs + new_objs]

        self.assertEqual(len(ids), len(set(ids)))

    def test_high_concurrency_generation(self):

        def create_obj():
            return AccessoryFactory.create().public_id

        with ThreadPoolExecutor(max_workers=20) as executor:
            ids = list(executor.map(lambda _: create_obj(), range(200)))

        self.assertEqual(len(ids), len(set(ids)))

    def test_bulk_with_many_manual_ids(self):

        objs = AccessoryFactory.build_batch(1000, room=None)

        for i in range(100):
            objs[i].public_id = f"ACMANUAL{i}"

        Accessory.objects.bulk_create(objs)

        manual_ids = [objs[i].public_id for i in range(100)]

        count = Accessory.objects.filter(public_id__in=manual_ids).count()

        self.assertEqual(count, 100)

    def test_massive_bulk_insert(self):

        start_count = Accessory.objects.count()

        objs = AccessoryFactory.build_batch(5000, room=None)

        Accessory.objects.bulk_create(objs)

        end_count = Accessory.objects.count()

        self.assertEqual(end_count - start_count, 5000)


    def test_bulk_create_query_count(self):
        objs = AccessoryFactory.build_batch(50, room=None)

        with CaptureQueriesContext(connection) as ctx:
            Accessory.objects.bulk_create(objs)

        self.assertLessEqual(len(ctx), 3)