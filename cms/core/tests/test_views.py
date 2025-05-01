import logging
from unittest import mock

from django.conf import settings
from django.test import Client, SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from fakeredis import FakeConnection
from wagtail.test.utils import WagtailTestUtils

from cms.home.models import HomePage


class CSRFTestCase(TestCase):
    """Tests for CSRF enforcement."""

    def setUp(self):
        # Client is created with each test to avoid mutation side-effects
        self.client = Client(enforce_csrf_checks=True)

    def test_csrf_token_mismatch_logs_an_error(self):
        """Check that the custom csrf error view logs CSRF failures."""
        self.client.cookies["csrftoken"] = "wrong"

        with self.assertLogs(logger="django.security.csrf", level=logging.ERROR) as logs:
            self.client.post("/admin/login/", {})

        self.assertIn("CSRF Failure: CSRF cookie", logs.output[0])


class TestGoogleTagManagerTestCase(TestCase):
    """Tests for the Google Tag Manager."""

    def test_google_tag_manager_script_present(self):
        """Check that the Google Tag Manager script and ID are present on the page.
        Note: this doesn't check the functionality, only presence.
        """
        response = self.client.get("/")

        self.assertIn("https://www.googletagmanager.com/gtm.js?id=", response.rendered_content)
        self.assertIn(settings.GOOGLE_TAG_MANAGER_CONTAINER_ID, response.rendered_content)


class ReadinessProbeTestCase(SimpleTestCase):
    """Tests for the readiness probe endpoint."""

    url = reverse("internal:readiness")

    def test_success(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"")
        self.assertEqual(response.templates, [])

    @override_settings(XFF_STRICT=True)
    def test_xff_exempt(self):
        # Send too many IPs
        x_forwarded_for = ",".join(["192.0.2.1"] * (settings.XFF_TRUSTED_PROXY_DEPTH + 1))
        response = self.client.get(self.url, headers={"X-Forwarded-For": x_forwarded_for})
        self.assertEqual(response.status_code, 204)


@override_settings(
    CACHES={
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": "redis://",
            "OPTIONS": {
                "CONNECTION_POOL_KWARGS": {"connection_class": FakeConnection},
            },
        }
    }
)
class LivenessProbeTestCase(TestCase):
    """Tests for the liveness probe endpoint."""

    databases = "__all__"

    url = reverse("internal:liveness")

    def test_success(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.content, b"")
        self.assertEqual(response.templates, [])

    @mock.patch("cms.core.views.DB_HEALTHCHECK_QUERY", "SELECT 0")
    def test_closed_database_fails(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.content, b"'default' database returned unexpected value.")

    @mock.patch("cms.core.views.DB_HEALTHCHECK_QUERY", "INVALID QUERY")
    def test_unexpected_database_error(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.content, b"'default' database connection errored unexpectedly.")

    @override_settings(
        CACHES={
            "default": {
                "BACKEND": "django_redis.cache.RedisCache",
                "LOCATION": "redis:///does-not-exist",
                "OPTIONS": {},
            }
        }
    )
    def test_broken_redis_connection(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.content, b"Failed to connect to cache.")

    @override_settings(XFF_STRICT=True)
    def test_xff_exempt(self):
        # Send too many IPs
        x_forwarded_for = ",".join(["192.0.2.1"] * (settings.XFF_TRUSTED_PROXY_DEPTH + 1))
        response = self.client.get(self.url, headers={"X-Forwarded-For": x_forwarded_for})
        self.assertEqual(response.status_code, 204)


class AdminPageTreeTestCase(WagtailTestUtils, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = cls.create_superuser(username="admin")

    def test_locale_label(self):
        """Check that the admin page tree is present on the page."""
        self.client.force_login(self.superuser)
        homepage = HomePage.objects.first()
        response = self.client.get(f"/admin/pages/{homepage.id}/")
        content = response.content.decode("utf-8")

        self.assertInHTML('<span class="w-status w-status--label w-m-0">English</span>', content)
