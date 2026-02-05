import logging
import platform
from datetime import UTC, datetime
from unittest import mock

import time_machine
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


class LivenessProbeTestCase(SimpleTestCase):
    """Tests for the liveness probe endpoint."""

    url = reverse("internal:liveness")

    def test_success(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"")
        self.assertEqual(response.templates, [])
        self.assertEqual(response.headers["Cache-Control"], "max-age=0, no-cache, no-store, must-revalidate, private")

    @override_settings(AWS_COGNITO_LOGIN_ENABLED=True, WAGTAIL_CORE_ADMIN_LOGIN_ENABLED=False)
    def test_success_cognito_login_enabled(self):
        self.test_success()

    @override_settings(XFF_STRICT=True)
    def test_xff_exempt(self):
        # Send too many IPs
        x_forwarded_for = ",".join(["192.0.2.1"] * (settings.XFF_TRUSTED_PROXY_DEPTH + 1))
        response = self.client.get(self.url, headers={"X-Forwarded-For": x_forwarded_for})
        self.assertEqual(response.status_code, 200)


@override_settings(
    CACHES={
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": "redis://",
            "OPTIONS": {
                "CONNECTION_POOL_KWARGS": {"connection_class": FakeConnection},
            },
        }
    },
)
class ReadinessProbeTestCase(TestCase):
    """Tests for the readiness probe endpoint."""

    databases = "__all__"

    url = reverse("internal:readiness")

    def test_success(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.headers["Cache-Control"], "max-age=0, no-cache, no-store, must-revalidate, private")

    @override_settings(AWS_COGNITO_LOGIN_ENABLED=True, WAGTAIL_CORE_ADMIN_LOGIN_ENABLED=False)
    def test_success_cognito_login_enabled(self):
        self.test_success()

    @mock.patch("cms.core.views.DB_HEALTHCHECK_QUERY", "SELECT 0")
    def test_closed_database_fails(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.content, b"Database default returned unexpected result")

    @mock.patch("cms.core.views.DB_HEALTHCHECK_QUERY", "INVALID QUERY")
    def test_unexpected_database_error(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.content, b"Database default reported an error")

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
        self.assertEqual(response.content, b"Unable to ping Redis")

    @override_settings(XFF_STRICT=True)
    def test_xff_exempt(self):
        # Send too many IPs
        x_forwarded_for = ",".join(["192.0.2.1"] * (settings.XFF_TRUSTED_PROXY_DEPTH + 1))
        response = self.client.get(self.url, headers={"X-Forwarded-For": x_forwarded_for})
        self.assertEqual(response.status_code, 200)


@override_settings(
    CACHES={
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": "redis://",
            "OPTIONS": {
                "CONNECTION_POOL_KWARGS": {"connection_class": FakeConnection},
            },
        }
    },
    BUILD_TIME=datetime(2000, 1, 1).astimezone(UTC),
    GIT_COMMIT="commit",
    START_TIME=datetime(2000, 1, 1).astimezone(UTC),
)
@time_machine.travel(datetime(2000, 1, 2), tick=False)
class HealthProbeTestCase(TestCase):
    """Tests for the health endpoint."""

    databases = "__all__"

    url = reverse("health")

    def test_success(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.templates, [])
        self.assertEqual(response.headers["Cache-Control"], "max-age=0, no-cache, no-store, must-revalidate, private")

        data = response.json()

        self.assertEqual(
            data["version"],
            {
                "build_time": "2000-01-01T00:00:00+00:00",
                "git_commit": "commit",
                "language": "python",
                "language_version": platform.python_version(),
            },
        )

        self.assertEqual(data["uptime"], 86400000)
        self.assertEqual(data["start_time"], "2000-01-01T00:00:00+00:00")

        self.assertEqual(data["status"], "OK")

        self.assertEqual(len(data["checks"]), 3)

        for check in data["checks"]:
            self.assertEqual(check["status"], "OK")
            self.assertEqual(check["status_code"], 200)
            self.assertTrue(check["message"].endswith("is ok"), check["message"])
            self.assertEqual(check["last_checked"], "2000-01-02T00:00:00+00:00")
            self.assertIsNone(check["last_failure"])
            self.assertEqual(check["last_success"], "2000-01-02T00:00:00+00:00")

    @override_settings(AWS_COGNITO_LOGIN_ENABLED=True, WAGTAIL_CORE_ADMIN_LOGIN_ENABLED=False)
    def test_success_cognito_login_enabled(self):
        self.test_success()

    @mock.patch("cms.core.views.DB_HEALTHCHECK_QUERY", "SELECT 0")
    def test_closed_database_fails(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 500)

        database_checks = [check for check in response.json()["checks"] if "database" in check["name"]]

        self.assertEqual(len(database_checks), 2)

        for check in database_checks:
            self.assertEqual(check["status"], "CRITICAL")
            self.assertEqual(check["status_code"], 500)
            self.assertEqual(check["message"], "Backend returned unexpected result")
            self.assertEqual(check["last_checked"], "2000-01-02T00:00:00+00:00")
            self.assertIsNone(check["last_success"])
            self.assertEqual(check["last_failure"], "2000-01-02T00:00:00+00:00")

    @mock.patch("cms.core.views.DB_HEALTHCHECK_QUERY", "INVALID QUERY")
    def test_unexpected_database_error(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 500)

        database_checks = [check for check in response.json()["checks"] if "database" in check["name"]]

        self.assertEqual(len(database_checks), 2)

        for check in database_checks:
            self.assertEqual(check["status"], "CRITICAL")
            self.assertEqual(check["status_code"], 500)
            self.assertEqual(check["message"], "Backend failed")
            self.assertEqual(check["last_checked"], "2000-01-02T00:00:00+00:00")
            self.assertIsNone(check["last_success"])
            self.assertEqual(check["last_failure"], "2000-01-02T00:00:00+00:00")

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

        cache_check = next(check for check in response.json()["checks"] if check["name"] == "cache")

        self.assertIsNotNone(cache_check)

        self.assertEqual(cache_check["status"], "CRITICAL")
        self.assertEqual(cache_check["status_code"], 500)
        self.assertEqual(cache_check["message"], "Ping failed")
        self.assertEqual(cache_check["last_checked"], "2000-01-02T00:00:00+00:00")
        self.assertIsNone(cache_check["last_success"])
        self.assertEqual(cache_check["last_failure"], "2000-01-02T00:00:00+00:00")

    @override_settings(XFF_STRICT=True)
    def test_xff_exempt(self):
        # Send too many IPs
        x_forwarded_for = ",".join(["192.0.2.1"] * (settings.XFF_TRUSTED_PROXY_DEPTH + 1))
        response = self.client.get(self.url, headers={"X-Forwarded-For": x_forwarded_for})
        self.assertEqual(response.status_code, 200)

    def test_alternate_url(self):
        response = self.client.get(reverse("internal:health"))
        self.assertEqual(response.status_code, 200)


class AdminPageTreeTestCase(WagtailTestUtils, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = cls.create_superuser(username="admin")
        cls.homepage = HomePage.objects.first()

    def setUp(self):
        self.client.force_login(self.superuser)

    def test_locale_label(self):
        """Check that the admin page tree is present on the page."""
        response = self.client.get(reverse("wagtailadmin_explore", args=[self.homepage.id]))
        content = response.content.decode("utf-8")

        self.assertInHTML('<span class="w-status w-status--label w-m-0">English</span>', content)

    def test_copy_page_does_not_have_publish_or_alias_options(self):
        """Test that the options to publish or copy as alias are removed via cms.core.forms.ONSCopyForm."""
        response = self.client.get(reverse("wagtailadmin_pages:copy", args=[self.homepage.id]))

        self.assertNotContains(response, "id_publish_copies")
        self.assertNotContains(response, "id_alias")
