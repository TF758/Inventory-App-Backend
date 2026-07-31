from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase
from django.urls import reverse


class HealthEndpointTests(SimpleTestCase):
    def test_liveness_returns_ok(self):
        response = self.client.get(reverse("health-live"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    @patch("core.health.MigrationExecutor")
    @patch("core.health.caches")
    @patch("core.health.connection")
    def test_readiness_returns_ok_when_dependencies_are_ready(
        self,
        mock_connection,
        mock_caches,
        mock_executor_class,
    ):
        cursor = MagicMock()
        mock_connection.cursor.return_value.__enter__.return_value = cursor

        cache = MagicMock()
        cache.get.return_value = "ok"
        mock_caches.__getitem__.return_value = cache

        executor = MagicMock()
        executor.loader.graph.leaf_nodes.return_value = []
        executor.migration_plan.return_value = []
        mock_executor_class.return_value = executor

        response = self.client.get(reverse("health-ready"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    @patch("core.health.MigrationExecutor")
    @patch("core.health.caches")
    @patch("core.health.connection")
    def test_readiness_returns_503_when_migrations_are_pending(
        self,
        mock_connection,
        mock_caches,
        mock_executor_class,
    ):
        cursor = MagicMock()
        mock_connection.cursor.return_value.__enter__.return_value = cursor

        cache = MagicMock()
        cache.get.return_value = "ok"
        mock_caches.__getitem__.return_value = cache

        executor = MagicMock()
        executor.loader.graph.leaf_nodes.return_value = []
        executor.migration_plan.return_value = [(object(), False)]
        mock_executor_class.return_value = executor

        response = self.client.get(reverse("health-ready"))

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["checks"]["migrations"], "pending")
