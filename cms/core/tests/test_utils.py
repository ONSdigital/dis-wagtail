from datetime import datetime

from django.test import RequestFactory, SimpleTestCase, TestCase, override_settings
from django.utils.formats import date_format

from cms.core.models.base import BasePage
from cms.core.utils import get_client_ip, get_formatted_pages_list


# DummyPage mimics the minimum attributes and methods of a Wagtail Page.
class DummyPage(BasePage):
    def __init__(self, title, summary="", listing_summary="", url="https://ons.gov.uk", **kwargs):  # pylint: disable=super-init-not-called
        # this just set attributes manually.
        self.title = title
        self.summary = summary
        self.listing_summary = listing_summary
        self._url = url
        self._release_date = kwargs.get("release_date")

    def get_url(self, request=None, current_site=None):
        return self._url

    @property
    def release_date(self):
        return self._release_date

    class Meta:
        abstract = True


class DummyPageWithNoReleaseDate(DummyPage):
    label = "Dummy Page"

    class Meta:
        abstract = True


class GetFormattedPagesListTests(TestCase):
    def test_without_release_date_and_listing_summary(self):
        # When no listing_summary and release_date, should use summary for description,
        # and use the default label.
        page = DummyPage(title="Test Page", summary="Test summary", listing_summary="")
        result = get_formatted_pages_list([page])
        expected = {
            "title": {"text": "Test Page", "url": "https://ons.gov.uk"},
            "metadata": {"object": {"text": "Page"}},
            "description": "Test summary",
        }
        self.assertEqual(len(result), 1)
        self.assertDictEqual(result[0], expected)

    def test_with_listing_summary_overrides_summary(self):
        # When listing_summary is provided, that should be used as description.
        page = DummyPage(title="Test Page", summary="Test summary", listing_summary="Listing summary")
        result = get_formatted_pages_list([page])
        expected = {
            "title": {"text": "Test Page", "url": "https://ons.gov.uk"},
            "metadata": {"object": {"text": "Page"}},
            "description": "Listing summary",
        }
        self.assertEqual(len(result), 1)
        self.assertDictEqual(result[0], expected)

    def test_with_custom_label(self):
        # When a custom label is defined, it should be used in metadata.
        page = DummyPageWithNoReleaseDate(title="Test Page", summary="Test summary", listing_summary="")
        result = get_formatted_pages_list([page])
        expected = {
            "title": {"text": "Test Page", "url": "https://ons.gov.uk"},
            "metadata": {"object": {"text": "Dummy Page"}},
            "description": "Test summary",
        }
        self.assertEqual(len(result), 1)
        self.assertDictEqual(result[0], expected)

    def test_with_release_date(self):
        # When release_date is provided, metadata should include date formatting.
        test_date = datetime(2024, 1, 1, 12, 30)
        page = DummyPage(title="Test Page", summary="Test summary", listing_summary="", release_date=test_date)
        result = get_formatted_pages_list([page])

        expected_iso = date_format(test_date, "c")
        expected_short = date_format(test_date, "DATE_FORMAT")

        expected = {
            "title": {"text": "Test Page", "url": "https://ons.gov.uk"},
            "metadata": {
                "object": {"text": "Page"},
                "date": {
                    "prefix": "Released",
                    "showPrefix": True,
                    "iso": expected_iso,
                    "short": expected_short,
                },
            },
            "description": "Test summary",
        }
        self.assertEqual(len(result), 1)
        self.assertDictEqual(result[0], expected)

    def test_multiple_pages(self):
        # Test processing multiple dummy pages
        test_date = datetime(2024, 1, 1, 12, 30)
        page1 = DummyPage(title="Page One", summary="Summary One", listing_summary="", release_date=test_date)
        page2 = DummyPageWithNoReleaseDate(title="Page Two", summary="Summary Two", listing_summary="Listing Two")
        pages = [page1, page2]
        result = get_formatted_pages_list(pages)

        expected_iso = date_format(test_date, "c")
        expected_short = date_format(test_date, "DATE_FORMAT")

        expected_page1 = {
            "title": {"text": "Page One", "url": "https://ons.gov.uk"},
            "metadata": {
                "object": {"text": "Page"},
                "date": {
                    "prefix": "Released",
                    "showPrefix": True,
                    "iso": expected_iso,
                    "short": expected_short,
                },
            },
            "description": "Summary One",
        }
        expected_page2 = {
            "title": {"text": "Page Two", "url": "https://ons.gov.uk"},
            "metadata": {"object": {"text": "Dummy Page"}},
            "description": "Listing Two",
        }
        self.assertEqual(len(result), 2)
        self.assertDictEqual(result[0], expected_page1)
        self.assertDictEqual(result[1], expected_page2)


class ClientIPTestCase(SimpleTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.factory = RequestFactory()

    def test_get_client_ip(self) -> None:
        request = self.factory.get("/")
        self.assertEqual(get_client_ip(request), "127.0.0.1")

    @override_settings(IS_EXTERNAL_ENV=True)
    def test_cannot_get_client_ip_in_external_env(self) -> None:
        request = self.factory.get("/")

        with self.assertRaisesMessage(RuntimeError, "Cannot get client IP in external environment."):
            get_client_ip(request)
