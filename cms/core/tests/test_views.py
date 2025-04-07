import logging
from http import HTTPMethod

from django.conf import settings
from django.db import connections
from django.test import Client, SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from fakeredis import FakeConnection


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

    def test_all_methods(self):
        """Check the ready endpoint works with all methods."""
        for method in iter(HTTPMethod):
            if method == HTTPMethod.CONNECT:
                # CONNECT isn't a valid method in this context
                continue

            with self.subTest(method):
                response = getattr(self.client, method.value.lower())(self.url)

                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.content, b"")
                self.assertEqual(response.templates, [])


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

    def test_all_methods(self):
        """Check the liveness endpoint works with all methods."""
        for method in iter(HTTPMethod):
            if method == HTTPMethod.CONNECT:
                # CONNECT isn't a valid method in this context
                continue

            with self.subTest(method):
                response = getattr(self.client, method.value.lower())(self.url)

                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.content, b"")
                self.assertEqual(response.templates, [])

    def test_fails(self):
        # Force close the connections to simulate a broken connection.
        for connection in connections.all():
            connection.close()

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.content, b"'default' database connection is not usable.")
