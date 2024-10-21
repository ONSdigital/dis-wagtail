import pytest
from wagtail.models import Site

from cms.core.context_processors import global_vars
from cms.core.models import Tracking

pytestmark = pytest.mark.django_db


def test_when_no_tracking_settings_defined(rf):
    request = rf.get("/")
    assert global_vars(request) == {
        "GOOGLE_TAG_MANAGER_ID": "",
        "SEO_NOINDEX": False,
        "LANGUAGE_CODE": "en-gb",
        "IS_EXTERNAL_ENV": False,
    }


def test_when_tracking_settings_defined(rf):
    Tracking.objects.create(
        site=Site.objects.get(is_default_site=True),
        google_tag_manager_id="GTM-123456",
    )
    request = rf.get("/")
    assert global_vars(request) == {
        "GOOGLE_TAG_MANAGER_ID": "GTM-123456",
        "SEO_NOINDEX": False,
        "LANGUAGE_CODE": "en-gb",
        "IS_EXTERNAL_ENV": False,
    }
