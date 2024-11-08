import logging

from django.conf import settings
from django.http.cookie import SimpleCookie
from django.test import Client, TestCase


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


class TestCookiesBannerTestCase(TestCase):
    """Test for the cookie banner functionality."""

    def setUp(self):
        self.client = Client()

    def test_google_tag_manager_script_present_when_tracking_consent_given(self):
        """Check that the Google Tag Manager script is present on the page when the user agrees to tracking."""
        self.client.cookies = SimpleCookie({"ons_cookie_policy": "'usage':true"})

        response = self.client.get("/")

        self.assertIn("https://www.googletagmanager.com/gtm.js?id=", response.rendered_content)
        self.assertIn(settings.GOOGLE_TAG_MANAGER_CONTAINER_ID, response.rendered_content)
