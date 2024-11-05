from django.test import RequestFactory, TestCase
from wagtail.models import Site

from cms.core.context_processors import global_vars
from cms.core.models import Tracking


class ContextProcessorTestCase(TestCase):
    """Tests for context processors."""
    def setUp(self):
        request_factory = RequestFactory()

        # Request is created with each test to avoid mutation side-effects
        self.request = request_factory.get("/")

    def test_when_no_tracking_settings_defined(self):
        """Check the global vars include sensible defaults when no Tracking settings defined."""
        self.assertEqual(global_vars(self.request)["GOOGLE_TAG_MANAGER_ID"], "")


    def test_when_tracking_settings_defined(self):
        """Confirm the global vars include Tracking settings when defined."""
        Tracking.objects.create(
            site=Site.objects.get(is_default_site=True),
            google_tag_manager_id="GTM-123456",
        )
        self.assertEqual(global_vars(self.request)["GOOGLE_TAG_MANAGER_ID"], "GTM-123456")


