from datetime import datetime

from django.conf import settings
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.utils import timezone
from django.utils.formats import date_format
from wagtail.test.utils import WagtailTestUtils

from cms.core.tests.factories import ContactDetailsFactory
from cms.methodology.tests.factories import MethodologyPageFactory


class MethodologyPageTestCase(WagtailTestUtils, TestCase):
    """Test MethodologyPage model properties and methods."""

    def setUp(self):
        self.basic_page = MethodologyPageFactory(
            parent__title="Topic Page",
            title="Methodology Page",
            publication_date=datetime(2024, 8, 15),
            show_cite_this_page=False,
            contact_details=None,
        )
        self.basic_page_url = self.basic_page.url

        self.page = MethodologyPageFactory(
            parent__title="Topic Page",
            title="Methodology Page",
            publication_date=datetime(2024, 8, 15),
            show_cite_this_page=True,
        )
        self.page_url = self.page.url

    # TOC
    def test_table_of_contents_with_content(self):
        """Test table_of_contents with content blocks."""
        self.basic_page.content = [
            {"type": "section", "value": {"title": "Test Section", "content": [{"type": "rich_text", "value": "text"}]}}
        ]

        self.assertIn({"url": "#test-section", "text": "Test Section"}, self.basic_page.table_of_contents)

    def test_table_of_contents_with_contact_details(self):
        """Test table_of_contents includes contact details when present."""
        self.page.contact_details = ContactDetailsFactory()
        toc = self.page.table_of_contents
        self.assertIn({"url": "#contact-details", "text": "Contact details"}, toc)

    # Cite this page block
    def test_cite_this_page_is_shown_when_ticked(self):
        """Test for the cite this page block."""
        latest_date_formatted = date_format(self.page.last_revised_date, settings.DATE_FORMAT)

        expected = (
            f"Office for National Statistics (ONS), last revised { latest_date_formatted }, "
            f'ONS website, methodology, <a href="{ self.page.full_url }">{ self.page.title }</a>'
        )
        response = self.client.get(self.page_url)
        self.assertContains(response, expected)

    def test_cite_this_page_is_not_shown_when_unticked(self):
        """Test for the cite this page block not present in the template."""
        self.basic_page.last_revised_date = self.basic_page.publication_date + timezone.timedelta(days=1)
        latest_date_formatted = date_format(self.basic_page.last_revised_date, settings.DATE_FORMAT)

        expected = (
            f"Office for National Statistics (ONS), last revised { latest_date_formatted }, "
            f'ONS website, methodology, <a href="{ self.page.full_url }">{ self.basic_page.title }</a>'
        )
        response = self.client.get(self.basic_page_url)
        self.assertNotContains(response, expected)

    # Dates
    def test_last_revised_date_must_be_after_publication_date(self):
        """Tests the model validates last revised date is after the publication date."""
        self.page.last_revised_date = self.page.publication_date

        with self.assertRaises(ValidationError) as info:
            self.page.clean()

        self.assertEqual(info.exception.messages, ["The last revised date must be after the published date."])

    # External environment
    @override_settings(IS_EXTERNAL_ENV=True)
    def test_render_in_external_env(self):
        """Test that the page renders in external environment."""
        response = self.client.get(self.page.url)

        self.assertEqual(response.status_code, 200)