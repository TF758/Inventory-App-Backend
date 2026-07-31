from django.conf import settings
from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase, override_settings
from rest_framework.permissions import AllowAny, IsAdminUser

from core.checks import production_boundary_checks
from core.middleware import OperationalEndpointSecurityMiddleware
from inventory.middleware import JWTAuthMiddleware
from inventory.urls import api_documentation_urlpatterns


class ProductionBoundarySettingsTests(SimpleTestCase):
    def test_non_development_settings_disable_basic_authentication(self):
        authentication_classes = settings.REST_FRAMEWORK[
            "DEFAULT_AUTHENTICATION_CLASSES"
        ]

        self.assertNotIn(
            "rest_framework.authentication.BasicAuthentication",
            authentication_classes,
        )

    def test_non_development_settings_disable_query_string_tokens(self):
        self.assertFalse(settings.WEBSOCKET_ALLOW_QUERY_TOKEN)

    def test_password_validator_baseline_is_enabled(self):
        validator_names = {
            validator["NAME"]
            for validator in settings.AUTH_PASSWORD_VALIDATORS
        }

        self.assertGreaterEqual(settings.PASSWORD_MIN_LENGTH, 10)
        self.assertIn(
            "django.contrib.auth.password_validation.CommonPasswordValidator",
            validator_names,
        )
        self.assertIn(
            "django.contrib.auth.password_validation.NumericPasswordValidator",
            validator_names,
        )

    @override_settings(API_DOCS_ENABLED=False)
    def test_disabled_api_documentation_has_no_routes(self):
        self.assertEqual(api_documentation_urlpatterns(), [])

    @override_settings(API_DOCS_ENABLED=True, API_DOCS_PUBLIC=True)
    def test_public_development_docs_use_allow_any(self):
        patterns = api_documentation_urlpatterns()
        self.assertEqual(len(patterns), 3)
        self.assertEqual(
            patterns[0].callback.initkwargs["permission_classes"],
            [AllowAny],
        )

    @override_settings(API_DOCS_ENABLED=True, API_DOCS_PUBLIC=False)
    def test_restricted_docs_require_admin_access(self):
        patterns = api_documentation_urlpatterns()
        self.assertEqual(
            patterns[0].callback.initkwargs["permission_classes"],
            [IsAdminUser],
        )


class MetricsBoundaryTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.middleware = OperationalEndpointSecurityMiddleware(
            lambda request: HttpResponse("ok")
        )

    @override_settings(
        METRICS_ALLOW_PUBLIC=False,
        METRICS_BEARER_TOKEN="metrics-secret",
    )
    def test_metrics_reject_missing_token(self):
        response = self.middleware(self.factory.get("/metrics"))
        self.assertEqual(response.status_code, 404)

    @override_settings(
        METRICS_ALLOW_PUBLIC=False,
        METRICS_BEARER_TOKEN="metrics-secret",
    )
    def test_metrics_accept_matching_bearer_token(self):
        request = self.factory.get(
            "/metrics",
            HTTP_AUTHORIZATION="Bearer metrics-secret",
        )
        response = self.middleware(request)
        self.assertEqual(response.status_code, 200)

    @override_settings(
        METRICS_ALLOW_PUBLIC=False,
        METRICS_BEARER_TOKEN="",
    )
    def test_empty_metrics_token_keeps_endpoint_disabled(self):
        request = self.factory.get(
            "/metrics",
            HTTP_AUTHORIZATION="Bearer anything",
        )
        response = self.middleware(request)
        self.assertEqual(response.status_code, 404)


class WebSocketTokenBoundaryTests(SimpleTestCase):
    @override_settings(WEBSOCKET_ALLOW_QUERY_TOKEN=False)
    def test_query_string_token_is_ignored(self):
        scope = {
            "subprotocols": [],
            "query_string": b"token=sensitive-token",
        }
        self.assertIsNone(JWTAuthMiddleware.extract_token(scope))

    @override_settings(WEBSOCKET_ALLOW_QUERY_TOKEN=True)
    def test_query_string_token_can_be_enabled_for_development(self):
        scope = {
            "subprotocols": [],
            "query_string": b"token=development-token",
        }
        self.assertEqual(
            JWTAuthMiddleware.extract_token(scope),
            "development-token",
        )

    @override_settings(WEBSOCKET_ALLOW_QUERY_TOKEN=False)
    def test_subprotocol_token_remains_supported(self):
        scope = {
            "subprotocols": ["jwt", "subprotocol-token"],
            "query_string": b"",
        }
        self.assertEqual(
            JWTAuthMiddleware.extract_token(scope),
            "subprotocol-token",
        )


@override_settings(
    STORAGE_BACKEND="filesystem",
    STORAGE_SHARED=True,
    STORAGE_IS_DISTRIBUTED=False,
    STORAGE_IS_SHARED=True,
    STORAGES={
        "default": {
            "BACKEND": (
                "django.core.files.storage.FileSystemStorage"
            ),
            "OPTIONS": {
                "location": settings.MEDIA_ROOT,
                "base_url": settings.MEDIA_URL,
            },
        },
        "reports": {
            "BACKEND": (
                "django.core.files.storage.FileSystemStorage"
            ),
            "OPTIONS": {
                "location": settings.REPORTS_DIR,
            },
        },
        "staticfiles": settings.STORAGES["staticfiles"],
    },
)
class DeploymentSecurityCheckTests(SimpleTestCase):
    def test_staging_security_boundaries_pass(self):
        rest_framework = {
            **settings.REST_FRAMEWORK,
            "DEFAULT_AUTHENTICATION_CLASSES": [
                (
                    "core.authentication."
                    "SessionJWTAuthentication"
                ),
                (
                    "rest_framework_simplejwt.authentication."
                    "JWTAuthentication"
                ),
                (
                    "rest_framework.authentication."
                    "SessionAuthentication"
                ),
            ],
        }

        with self.settings(
            APP_ENV="staging",
            ENABLE_BASIC_AUTH=False,
            REST_FRAMEWORK=rest_framework,
            WEBSOCKET_ALLOW_QUERY_TOKEN=False,
            METRICS_ALLOW_PUBLIC=False,
            METRICS_BEARER_TOKEN="metrics-secret",
            API_DOCS_PUBLIC=False,
        ):
            messages = production_boundary_checks(None)

        errors = [message for message in messages if message.is_serious()]
        self.assertEqual(errors, [])

    @override_settings(
        APP_ENV="staging",
        WEBSOCKET_ALLOW_QUERY_TOKEN=True,
        METRICS_ALLOW_PUBLIC=True,
        API_DOCS_PUBLIC=True,
        METRICS_BEARER_TOKEN="metrics-secret",
    )
    def test_unsafe_staging_boundaries_fail_deployment_checks(self):
        messages = production_boundary_checks(None)
        message_ids = {message.id for message in messages}

        self.assertIn("inventory.E002", message_ids)
        self.assertIn("inventory.E003", message_ids)
        self.assertIn("inventory.E004", message_ids)