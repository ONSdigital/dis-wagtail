from django.conf import settings
from django.test import RequestFactory, TestCase

from cms.auth.utils import get_auth_config
from cms.core.context_processors import global_vars


class ContextProcessorTestCase(TestCase):
    """Tests for context processors."""

    def setUp(self):
        request_factory = RequestFactory()

        # Request is created with each test to avoid mutation side-effects
        self.request = request_factory.get("/")

    def test_context_processor_picks_up_variables_from_env(self):
        """Check that the context processor correctly picks up environment variables."""
        expected = {
            "GOOGLE_TAG_MANAGER_CONTAINER_ID": settings.GOOGLE_TAG_MANAGER_CONTAINER_ID,
            "ONS_COOKIE_BANNER_SERVICE_NAME": settings.ONS_COOKIE_BANNER_SERVICE_NAME,
            "SEO_NOINDEX": False,
            "LANGUAGE_CODE": "en-gb",
            "IS_EXTERNAL_ENV": False,
            "AWS_COGNITO_LOGIN_ENABLED": settings.AWS_COGNITO_LOGIN_ENABLED,
            "WAGTAIL_CORE_ADMIN_LOGIN_ENABLED": settings.WAGTAIL_CORE_ADMIN_LOGIN_ENABLED,
            "AUTH_CONFIG": get_auth_config(),
            "DEFAULT_OG_IMAGE_URL": settings.DEFAULT_OG_IMAGE_URL,
            "CONTACT_US_URL": settings.CONTACT_US_URL,
            "BACKUP_SITE_URL": settings.BACKUP_SITE_URL,
            "ONS_SEARCH_REDIRECT_PATH": settings.ONS_SEARCH_REDIRECT_PATH,
            "COOKIES_PAGE_URL": f"/{settings.ONS_COOKIES_PAGE_SLUG}",
        }
        self.assertEqual(global_vars(self.request), expected)
