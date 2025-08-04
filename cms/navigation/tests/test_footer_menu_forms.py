import uuid

from django.test import TestCase
from wagtail.admin.panels import get_edit_handler
from wagtail.test.utils.form_data import nested_form_data, streamfield

from cms.navigation.models import FooterMenu
from cms.navigation.tests.factories import (
    FooterMenuFactory,
    ThemePageFactory,
)


class BaseFooterMenuTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.footer_menu = FooterMenuFactory()
        cls.form_class = get_edit_handler(FooterMenu).get_form_class()

        cls.theme_page_1 = ThemePageFactory()
        cls.theme_page_2 = ThemePageFactory(parent=cls.theme_page_1.get_parent())

        cls.example_url_1 = "https://example.com"
        cls.example_url_2 = "https://example2.com"

    def raw_form_data(self, columns_data: None) -> dict:
        """Returns the raw form data for the FooterMenu form."""
        columns_data = columns_data or []
        return {"columns": streamfield(columns_data)}

    def create_link(self, page_pk, external_url, link_title, order=0):
        return {
            "id": str(uuid.uuid4()),
            "type": "item",
            "value": {
                "page": page_pk,
                "external_url": external_url,
                "title": link_title,
            },
            "deleted": "",
            "order": str(order),
        }

    def create_links_column(self, title, links=None):
        """Creates a dictionary representing a single LinksColumn block.
        links should be a list of link dicts (as created by `create_link`).
        """
        return {
            "title": title,
            "links": links or [],
            # Wagtail's ListBlock in form data often uses <field>-count to track items
            "links-count": len(links) if links else 0,
        }


class FooterMenuColumnsTests(BaseFooterMenuTestCase):
    def test_duplicate_pages_across_column(self):
        """Checks that using the same pages in the different columns raises a duplicate error."""
        column_1_links = [self.create_link(page_pk=self.theme_page_1.pk, external_url="", link_title="Link #1")]

        raw_data = self.raw_form_data(
            columns_data=[
                ("column", self.create_links_column(title="Column 1", links=column_1_links)),
                ("column", self.create_links_column(title="Column 2", links=column_1_links)),
            ]
        )

        form = self.form_class(
            instance=self.footer_menu,
            data=nested_form_data(raw_data),
        )

        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors["columns"]
            .data[0]
            .block_errors[1]
            .block_errors["links"]
            .block_errors[0]
            .block_errors["page"]
            .message,
            "Duplicate page. Please choose a different one.",
        )

    def test_no_duplicate_pages_across_columns(self):
        """Ensures that two columns having different pages do not trigger
        the duplicate pages validation error.
        """
        column_1_links = [self.create_link(page_pk=self.theme_page_1.pk, external_url="", link_title="Link #1")]
        column_2_links = [self.create_link(page_pk=self.theme_page_2.pk, external_url="", link_title="Link #2")]

        raw_data = self.raw_form_data(
            columns_data=[
                ("column", self.create_links_column(title="Column 1", links=column_1_links)),
                ("column", self.create_links_column(title="Column 2", links=column_2_links)),
            ]
        )

        form = self.form_class(
            instance=self.footer_menu,
            data=nested_form_data(raw_data),
        )

        self.assertTrue(form.is_valid(), msg=form.errors.as_json())

    def test_duplicate_pages_in_same_column(self):
        """Checks that the same pages used in the same column raises a duplicate error."""
        column_1_links = [
            self.create_link(page_pk=self.theme_page_1.pk, external_url="", link_title="Link #1"),
            self.create_link(page_pk=self.theme_page_1.pk, external_url="", link_title="Link #2", order=1),
        ]

        raw_data = self.raw_form_data(
            columns_data=[
                ("column", self.create_links_column(title="Column 1", links=column_1_links)),
            ]
        )

        form = self.form_class(
            instance=self.footer_menu,
            data=nested_form_data(raw_data),
        )

        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors["columns"]
            .data[0]
            .block_errors[0]
            .block_errors["links"]
            .block_errors[1]
            .block_errors["page"]
            .message,
            "Duplicate page. Please choose a different one.",
        )

    def test_no_duplicate_pages_in_same_column(self):
        """Check that different pages in the same column do not trigger any validation errors."""
        column_1_links = [
            self.create_link(page_pk=self.theme_page_1.pk, external_url="", link_title="Link #1"),
            self.create_link(page_pk=self.theme_page_2.pk, external_url="", link_title="Link #2", order=1),
        ]

        raw_data = self.raw_form_data(
            columns_data=[
                ("column", self.create_links_column(title="Column 1", links=column_1_links)),
            ]
        )

        form = self.form_class(
            instance=self.footer_menu,
            data=nested_form_data(raw_data),
        )

        self.assertTrue(form.is_valid(), msg=form.errors.as_json())

    def test_no_duplicate_urls_across_columns(self):
        """Ensures that two columns having different external URLs do not trigger
        the duplicate URL validation error.
        """
        column_1_links = [self.create_link(page_pk="", external_url=self.example_url_1, link_title="Link #1")]
        column_2_links = [self.create_link(page_pk="", external_url=self.example_url_2, link_title="Link #2")]

        raw_data = self.raw_form_data(
            columns_data=[
                ("column", self.create_links_column("Column 1", column_1_links)),
                ("column", self.create_links_column("Column 2", column_2_links)),
            ]
        )

        form = self.form_class(instance=self.footer_menu, data=nested_form_data(raw_data))
        self.assertTrue(form.is_valid(), msg=form.errors.as_json())

    def test_duplicate_urls_across_column(self):
        """Checks that using the same external URLs in the different columns raises a duplicate error."""
        column_1_links = [
            self.create_link(page_pk="", external_url=self.example_url_1, link_title="Link #1"),
            self.create_link(page_pk="", external_url=self.example_url_2, link_title="Link #2", order=1),
        ]
        column_2_links = [self.create_link(page_pk="", external_url=self.example_url_2, link_title="Link #2")]

        raw_data = self.raw_form_data(
            columns_data=[
                ("column", self.create_links_column("Column 1", column_1_links)),
                ("column", self.create_links_column("Column 2", column_2_links)),
            ]
        )

        form = self.form_class(instance=self.footer_menu, data=nested_form_data(raw_data))
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors["columns"]
            .data[0]
            .block_errors[1]
            .block_errors["links"]
            .block_errors[0]
            .block_errors["external_url"]
            .message,
            "Duplicate URL. Please add a different one.",
        )

    def test_duplicate_urls_in_same_column(self):
        """Checks that the same external URLs used in the same column raises a duplicate error."""
        column_1_links = [
            self.create_link(page_pk="", external_url=self.example_url_1, link_title="Link #1"),
            self.create_link(page_pk="", external_url=self.example_url_1, link_title="Link #2", order=1),
        ]

        raw_data = self.raw_form_data(
            columns_data=[
                ("column", self.create_links_column("Column 1", column_1_links)),
            ]
        )

        form = self.form_class(instance=self.footer_menu, data=nested_form_data(raw_data))
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors["columns"]
            .data[0]
            .block_errors[0]
            .block_errors["links"]
            .block_errors[1]
            .block_errors["external_url"]
            .message,
            "Duplicate URL. Please add a different one.",
        )

    def test_no_duplicate_urls_in_same_column(self):
        """Check that different external URLs in the same column do not trigger any validation errors."""
        column_1_links = [
            self.create_link(page_pk="", external_url=self.example_url_1, link_title="Link #1"),
            self.create_link(page_pk="", external_url=self.example_url_2, link_title="Link #2", order=1),
        ]

        raw_data = self.raw_form_data(
            columns_data=[
                ("column", self.create_links_column("Column 1", column_1_links)),
            ]
        )

        form = self.form_class(instance=self.footer_menu, data=nested_form_data(raw_data))
        self.assertTrue(form.is_valid(), msg=form.errors.as_json())
