from datetime import datetime

from django.conf import settings
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.utils.formats import date_format
from wagtail.test.utils import WagtailTestUtils

from cms.core.permission_testers import BasePagePermissionTester
from cms.core.tests.factories import ContactDetailsFactory
from cms.methodology.tests.factories import MethodologyPageFactory, MethodologyRelatedPageFactory
from cms.users.tests.factories import UserFactory


class MethodologyPageTestCase(WagtailTestUtils, TestCase):
    """Test MethodologyPage model properties and methods."""

    def setUp(self):
        self.page = MethodologyPageFactory(
            parent__title="Topic Page",
            title="Methodology Page",
            publication_date=datetime(2024, 8, 15),
            show_cite_this_page=False,
            contact_details=None,
        )
        self.page_url = self.page.url

    def test_permission_tester_inherits_from_basepagepermissiontester(self):
        self.assertIsInstance(self.page.permissions_for_user(UserFactory()), BasePagePermissionTester)

    def test_table_of_contents_with_content(self):
        """Test table_of_contents with content blocks."""
        self.page.content = [
            {"type": "section", "value": {"title": "Test Section", "content": [{"type": "rich_text", "value": "text"}]}}
        ]

        toc = self.page.table_of_contents
        self.assertEqual(len(toc), 1)
        toc_item = toc[0]
        self.assertEqual(toc_item["url"], "#test-section")
        self.assertEqual(toc_item["text"], "Test Section")

    def test_table_of_contents_with_contact_details(self):
        """Test table_of_contents includes contact details when present."""
        self.page.contact_details = ContactDetailsFactory()
        toc = self.page.table_of_contents
        self.assertEqual(len(toc), 1)
        toc_item = toc[0]
        self.assertEqual(toc_item["url"], "#contact-details")
        self.assertEqual(toc_item["text"], "Contact details")

    def test_table_of_contents_without_related_publications(self):
        MethodologyRelatedPageFactory(parent=self.page)
        toc = self.page.table_of_contents
        self.assertEqual(len(toc), 1)
        toc_item = toc[0]
        self.assertEqual(toc_item["url"], "#related-publications")
        self.assertEqual(toc_item["text"], "Related publications")

    def test_cite_this_page_is_not_shown_when_unticked(self):
        """Test for the cite this page block not present in the template."""
        latest_date_formatted = date_format(self.page.last_revised_date, settings.DATE_FORMAT)

        cite_fragment = (
            f"Office for National Statistics (ONS), last revised {latest_date_formatted}, "
            f'ONS website, methodology, <a href="{self.page.full_url}">{self.page.title}</a>'
        )
        response = self.client.get(self.page_url)
        self.assertNotContains(response, cite_fragment)

    def test_cite_this_page_is_shown_when_ticked(self):
        """Test for the cite this page block."""
        self.page.show_cite_this_page = True
        self.page.save(update_fields=["show_cite_this_page"])
        latest_date_formatted = date_format(self.page.last_revised_date, settings.DATE_FORMAT)

        cite_fragment = (
            f"Office for National Statistics (ONS), last revised {latest_date_formatted}, "
            f'ONS website, methodology, <a href="{self.page.full_url}">{self.page.title}</a>'
        )
        response = self.client.get(self.page_url)
        self.assertContains(response, cite_fragment)

    def test_last_revised_date_must_be_after_publication_date(self):
        """Tests the model validates last revised date is after the publication date."""
        self.page.last_revised_date = self.page.publication_date

        with self.assertRaises(ValidationError) as info:
            self.page.clean()

        self.assertEqual(info.exception.messages, ["The last revised date must be after the published date."])

    def test_related_publications(self):
        related = [
            MethodologyRelatedPageFactory(parent=self.page, page__title="Article Series 1"),
            MethodologyRelatedPageFactory(parent=self.page, page__title="Another Article Series 2"),
            MethodologyRelatedPageFactory(parent=self.page, page__title="Unpublished Article Series", page__live=False),
        ]

        self.assertListEqual(
            list(self.page.related_publications.values_list("pk", flat=True)), [related[0].page_id, related[1].page_id]
        )

    def test_get_formatted_related_publications_list(self):
        related = MethodologyRelatedPageFactory(parent=self.page, page__title="The Article Series 1")

        self.assertEqual(
            self.page.get_formatted_related_publications_list(),
            {
                "title": "Related publications",
                "itemsList": [{"title": related.page.display_title, "url": related.page.url}],
            },
        )

    @override_settings(IS_EXTERNAL_ENV=True)
    def test_render_in_external_env(self):
        """Test that the page renders in external environment."""
        response = self.client.get(self.page_url)

        self.assertEqual(response.status_code, 200)
