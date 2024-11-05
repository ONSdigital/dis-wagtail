import os

from django.test import RequestFactory, TestCase

from cms.core.context_processors import global_vars


class ContextProcessorTestCase(TestCase):
    """Tests for context processors."""

    def setUp(self):
        request_factory = RequestFactory()

        # Request is created with each test to avoid mutation side-effects
        self.request = request_factory.get("/")

    def test_defaults_when_no_environment_settings_defined(self):
        """Check the global vars include sensible defaults when no environment settings defined."""
        self.assertEqual(
            global_vars(self.request),
            {
                "GOOGLE_TAG_MANAGER_ID": "",
                "SEO_NOINDEX": False,
                "LANGUAGE_CODE": "en-gb",
                "IS_EXTERNAL_ENV": False,
            },
        )

    def test_custom_values_when_environment_settings_defined(self):
        """Confirm the global vars include environment settings when defined."""
        os.environ["GOOGLE_TAG_MANAGER_ID"] = "GTM-123456"

        self.assertEqual(
            global_vars(self.request),
            {
                "GOOGLE_TAG_MANAGER_ID": "GTM-123456",
                "SEO_NOINDEX": False,
                "LANGUAGE_CODE": "en-gb",
                "IS_EXTERNAL_ENV": False,
            },
        )
