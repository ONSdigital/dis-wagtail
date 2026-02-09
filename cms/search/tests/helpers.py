"""Shared constants and assertion mixins for search resource tests.
Keep everything that describes the shape of the resource metadata
dict in this file so all tests agree on a single truth.
"""

import json

from django.test import SimpleTestCase, override_settings
from django.utils.html import strip_tags
from wagtail.models import Page

from cms.search.utils import build_page_uri

EXPECTED_CONTENT_TYPES = {
    "ReleaseCalendarPage": "release",
    "StatisticalArticlePage": "statistical_article",
    "InformationPage": "static_page",
    "IndexPage": "static_page",
    "MethodologyPage": "static_methodology",
    "TopicPage": "product_page",
}


class ResourceDictAssertions(SimpleTestCase):
    """Mixin that provides shared assertions for the resource metadata dict.
    - Inheriting from SimpleTestCase gives us all the assert helpers (silences pylint/mypy).
    mixin as a runnable test case.
    """

    def assert_base_fields(self, payload: dict, page: Page, title=None) -> None:
        self.assertIn("uri", payload)
        self.assertIn("title", payload)
        self.assertIn("summary", payload)
        self.assertIn("content_type", payload)
        self.assertIn("topics", payload)
        self.assertIn("language", payload)

        self.assertEqual(payload["uri"], build_page_uri(page))
        expected_title = title if title is not None else page.title
        self.assertEqual(payload["title"], expected_title)

        # The resource builder uses get_text_for_indexing() for search/Kafka payloads,
        # so we only strip the source summary for comparison instead of re-sanitising.
        self.assertEqual(payload["summary"], strip_tags(page.summary))

        expected_ct = EXPECTED_CONTENT_TYPES[type(page).__name__]
        self.assertEqual(payload["content_type"], expected_ct)
        self.assertIsInstance(payload["topics"], list)
        self.assertEqual(payload["language"], page.locale.get_display_name())

        release_date = getattr(page, "release_date", page.last_published_at)
        self.assertEqual(payload["release_date"], release_date.isoformat())

    def assert_release_fields_present(self, payload: dict) -> None:
        for key in ("release_date", "finalised", "cancelled", "published", "date_changes"):
            self.assertIn(key, payload)

    def assert_release_booleans(
        self, payload: dict, *, finalised: bool = False, cancelled: bool = False, published: bool = False
    ) -> None:
        self.assertEqual(payload["finalised"], finalised)
        self.assertEqual(payload["cancelled"], cancelled)
        self.assertEqual(payload["published"], published)


class ExternalAPITestMixin:
    """Helpers for calling an endpoint “as if” we were on the external
    publishing stack (IS_EXTERNAL_ENV=True) and for decoding JSON.
    """

    EXTERNAL_URLCONF = "cms.search.tests.test_urls"

    def call_view_as_external(self, url, **extra):
        """Issue a GET with the same client but under
          - ROOT_URLCONF = EXTERNAL_URLCONF
          - IS_EXTERNAL_ENV = True
        so the view passes its environment check.
        """
        with override_settings(
            ROOT_URLCONF=self.EXTERNAL_URLCONF,
            IS_EXTERNAL_ENV=True,
        ):
            return self.client.get(url, **extra)

    @staticmethod
    def parse_json(response):
        """Return response.body decoded as JSON."""
        return json.loads(response.content)
