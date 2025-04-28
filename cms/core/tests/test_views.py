import logging
from http import HTTPMethod

from django.conf import settings
from django.test import Client, SimpleTestCase, TestCase
from django.urls import reverse
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

    def test_all_methods(self):
        """Check the ready endpoint works with all methods."""
        for method in iter(HTTPMethod):
            if method == HTTPMethod.CONNECT:
                # CONNECT isn't a valid method in this context
                continue

            with self.subTest(method):
                response = getattr(self.client, method.value.lower())(self.url)

                self.assertEqual(response.status_code, 204)
                self.assertEqual(response.content, b"")
                self.assertEqual(response.templates, [])


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
