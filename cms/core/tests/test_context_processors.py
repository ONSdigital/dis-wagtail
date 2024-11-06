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
                "GOOGLE_TAG_MANAGER_CONTAINER_ID": "",
                "ONS_COOKIE_BANNER_SERVICE_NAME": "www.ons.gov.uk",
                "MANAGE_COOKIE_SETTINGS_URL": "https://www.ons.gov.uk/cookies",
                "SEO_NOINDEX": False,
                "LANGUAGE_CODE": "en-gb",
                "IS_EXTERNAL_ENV": False,
            },
        )
