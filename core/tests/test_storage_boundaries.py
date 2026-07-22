from django.test import SimpleTestCase, override_settings

from core.checks import production_boundary_checks


VALID_STORAGE_ALIASES = {
    "default": {
        "BACKEND": "django.core.files.storage.InMemoryStorage",
    },
    "reports": {
        "BACKEND": "django.core.files.storage.InMemoryStorage",
    },
    "staticfiles": {
        "BACKEND": (
            "django.contrib.staticfiles.storage.StaticFilesStorage"
        ),
    },
}


def storage_messages(**settings_overrides):
    defaults = {
        "APP_ENV": "staging",
        "STORAGES": VALID_STORAGE_ALIASES,
        "STORAGE_BACKEND": "filesystem",
        "STORAGE_SHARED": True,
        "AWS_STORAGE_BUCKET_NAME": "",
        "AWS_S3_ENDPOINT_URL": "",
        "AWS_S3_USE_SSL": True,
        "AWS_S3_VERIFY": True,
        "METRICS_BEARER_TOKEN": "metrics-secret",
    }
    defaults.update(settings_overrides)

    with override_settings(**defaults):
        return production_boundary_checks(None)


class StorageDeploymentBoundaryTests(SimpleTestCase):
    def assert_has_message(self, messages, message_id):
        self.assertIn(message_id, {message.id for message in messages})

    def assert_lacks_message(self, messages, message_id):
        self.assertNotIn(message_id, {message.id for message in messages})

    def test_required_storage_aliases_are_enforced(self):
        messages = storage_messages(
            STORAGES={
                "default": VALID_STORAGE_ALIASES["default"],
            }
        )

        self.assert_has_message(messages, "inventory.E010")

    def test_unknown_storage_backend_is_rejected(self):
        messages = storage_messages(STORAGE_BACKEND="unknown")

        self.assert_has_message(messages, "inventory.E011")

    def test_unshared_filesystem_storage_is_rejected(self):
        messages = storage_messages(STORAGE_SHARED=False)

        self.assert_has_message(messages, "inventory.E012")

    def test_shared_filesystem_storage_is_valid_for_staging(self):
        messages = storage_messages(STORAGE_SHARED=True)

        self.assert_lacks_message(messages, "inventory.E012")

    def test_s3_storage_requires_a_bucket(self):
        messages = storage_messages(
            STORAGE_BACKEND="s3",
            AWS_STORAGE_BUCKET_NAME="",
        )

        self.assert_has_message(messages, "inventory.E013")

    def test_s3_storage_accepts_a_bucket_in_staging(self):
        messages = storage_messages(
            STORAGE_BACKEND="s3",
            AWS_STORAGE_BUCKET_NAME="inventory-staging",
        )

        self.assert_lacks_message(messages, "inventory.E013")

    def test_production_s3_endpoint_requires_https(self):
        messages = storage_messages(
            APP_ENV="production",
            STORAGE_BACKEND="s3",
            AWS_STORAGE_BUCKET_NAME="inventory-production",
            AWS_S3_ENDPOINT_URL="http://object-storage.internal",
        )

        self.assert_has_message(messages, "inventory.E014")

    def test_production_s3_requires_tls_verification(self):
        messages = storage_messages(
            APP_ENV="production",
            STORAGE_BACKEND="s3",
            AWS_STORAGE_BUCKET_NAME="inventory-production",
            AWS_S3_ENDPOINT_URL="https://object-storage.example.com",
            AWS_S3_USE_SSL=False,
            AWS_S3_VERIFY=False,
        )

        self.assert_has_message(messages, "inventory.E015")
        self.assert_has_message(messages, "inventory.E016")
