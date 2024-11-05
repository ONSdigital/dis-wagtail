import pytest
from wagtail.models import Site

from cms.core.context_processors import global_vars
from cms.core.models import Tracking

pytestmark = pytest.mark.django_db


def test_when_no_tracking_settings_defined(rf):
    """Check the global vars include sensible defaults when no Tracking settings defined."""
    request = RequestFactory().get("/")
    result = global_vars(request)
    self.assertEqual(result["GOOGLE_TAG_MANAGER_ID"], "")


def test_when_tracking_settings_defined(rf):
    """Confirm the global vars include Tracking settings when defined."""
    Tracking.objects.create(
        site=Site.objects.get(is_default_site=True),
        google_tag_manager_id="GTM-123456",
    )
    request = RequestFactory().get("/")
    result = global_vars(request)
    self.assertEqual(result["GOOGLE_TAG_MANAGER_ID"], "")
