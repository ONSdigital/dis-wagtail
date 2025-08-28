from datetime import datetime

from django.test import TestCase
from django.utils.formats import date_format

from cms.core.custom_date_format import ons_date_format
from cms.core.formatting_utils import format_as_document_list_item, get_formatted_pages_list
from cms.core.models.base import BasePage


# DummyPage mimics the minimum attributes and methods of a Wagtail Page.
class DummyPage(BasePage):
    def __init__(self, title, summary="", listing_summary="", url="https://ons.gov.uk", **kwargs):
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
        page_dict = {"internal_page": page}
        result = get_formatted_pages_list([page_dict])
        expected = {
            "title": {"text": "Test Page", "url": "https://ons.gov.uk"},
            "metadata": {"object": {"text": "Page"}},
            "description": "<p>Test summary</p>",
        }
        self.assertEqual(len(result), 1)
        self.assertDictEqual(result[0], expected)

    def test_with_listing_summary_overrides_summary(self):
        # When listing_summary is provided, that should be used as description.
        page = DummyPage(title="Test Page", summary="Test summary", listing_summary="Listing summary")
        page_dict = {"internal_page": page}
        result = get_formatted_pages_list([page_dict])
        expected = {
            "title": {"text": "Test Page", "url": "https://ons.gov.uk"},
            "metadata": {"object": {"text": "Page"}},
            "description": "<p>Listing summary</p>",
        }
        self.assertEqual(len(result), 1)
        self.assertDictEqual(result[0], expected)

    def test_with_custom_label(self):
        # When a custom label is defined, it should be used in metadata.
        page = DummyPageWithNoReleaseDate(title="Test Page", summary="Test summary", listing_summary="")
        page_dict = {"internal_page": page}
        result = get_formatted_pages_list([page_dict])
        expected = {
            "title": {"text": "Test Page", "url": "https://ons.gov.uk"},
            "metadata": {"object": {"text": "Dummy Page"}},
            "description": "<p>Test summary</p>",
        }
        self.assertEqual(len(result), 1)
        self.assertDictEqual(result[0], expected)

    def test_with_release_date(self):
        # When release_date is provided, metadata should include date formatting.
        test_date = datetime(2024, 1, 1, 12, 30)
        page = DummyPage(title="Test Page", summary="Test summary", listing_summary="", release_date=test_date)
        page_dict = {"internal_page": page}
        result = get_formatted_pages_list([page_dict])

        expected_iso = date_format(test_date, "c")
        expected_short = ons_date_format(test_date, "DATE_FORMAT")

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
            "description": "<p>Test summary</p>",
        }
        self.assertEqual(len(result), 1)
        self.assertDictEqual(result[0], expected)

    def test_multiple_pages(self):
        # Test processing multiple dummy pages
        test_date = datetime(2024, 1, 1, 12, 30)
        page1 = DummyPage(title="Page One", summary="Summary One", listing_summary="", release_date=test_date)
        page2 = DummyPageWithNoReleaseDate(title="Page Two", summary="Summary Two", listing_summary="Listing Two")
        pages = [{"internal_page": page1}, {"internal_page": page2}]
        result = get_formatted_pages_list(pages)

        expected_iso = date_format(test_date, "c")
        expected_short = ons_date_format(test_date, "DATE_FORMAT")

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
            "description": "<p>Summary One</p>",
        }
        expected_page2 = {
            "title": {"text": "Page Two", "url": "https://ons.gov.uk"},
            "metadata": {"object": {"text": "Dummy Page"}},
            "description": "<p>Listing Two</p>",
        }
        self.assertEqual(len(result), 2)
        self.assertDictEqual(result[0], expected_page1)
        self.assertDictEqual(result[1], expected_page2)

    def test_internal_page_dict_format(self):
        """Test processing dict with internal_page key."""
        page = DummyPage(title="Test Page", summary="Test summary")
        page_dict = {"internal_page": page}
        result = get_formatted_pages_list([page_dict])

        expected = {
            "title": {"text": "Test Page", "url": "https://ons.gov.uk"},
            "metadata": {"object": {"text": "Page"}},
            "description": "<p>Test summary</p>",
        }
        self.assertEqual(len(result), 1)
        self.assertDictEqual(result[0], expected)

    def test_internal_page_dict_format_with_custom_title(self):
        """Test processing dict with internal_page and custom title."""
        page = DummyPage(title="Original Title", summary="Test summary")
        page_dict = {"internal_page": page, "title": "Custom Title"}
        result = get_formatted_pages_list([page_dict])

        expected = {
            "title": {"text": "Custom Title", "url": "https://ons.gov.uk"},
            "metadata": {"object": {"text": "Page"}},
            "description": "<p>Test summary</p>",
        }
        self.assertEqual(len(result), 1)
        self.assertDictEqual(result[0], expected)


class TestFormatAsDocumentListItem(TestCase):
    def test_format_as_document_list_item(self):
        """Test helper function to format data to match the ONS Document List design system component."""
        title = "Element"
        url = "https://example.com/"
        content_type = "Data type"
        description = "This is a description."

        formatted_element = format_as_document_list_item(
            title=title, url=url, content_type=content_type, description=description
        )

        expected = {
            "title": {"text": title, "url": url},
            "metadata": {"object": {"text": content_type}},
            "description": f"<p>{description}</p>",
        }

        self.assertEqual(formatted_element, expected)
