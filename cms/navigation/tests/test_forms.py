from django.test import TestCase
from wagtail.test.utils.form_data import nested_form_data, streamfield

from cms.navigation.forms import MainMenuAdminForm
from wagtail.admin.panels import get_edit_handler
from cms.navigation.models import MainMenu
from cms.navigation.tests.factories import (
    MainMenuFactory,
    ThemePageFactory,
    TopicPageFactory,
)


class MainMenuAdminFormTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.menu = MainMenuFactory()
        cls.form_class = get_edit_handler(MainMenu).get_form_class()

    def raw_form_data(self, highlights_data=None, columns_data=None) -> dict:
        highlights_data = highlights_data or []
        columns_data = columns_data or []

        return {
            "highlights": streamfield(highlights_data),
            "columns": streamfield(columns_data),
        }

    def test_clean_highlights_no_duplicates(self):
        """Checks that different pages in the highlights do not trigger any validation errors."""
        page1 = ThemePageFactory()
        page2 = ThemePageFactory()

        raw_data = self.raw_form_data(
            highlights_data=[
                (
                    "highlight",
                    {
                        "page": page1.pk,
                        "external_url": "",
                        "description": "Highlight 1",
                    },
                ),
                (
                    "highlight",
                    {
                        "page": page2.pk,
                        "external_url": "",
                        "description": "Highlight 2",
                    },
                ),
            ]
        )

        form = self.form_class(instance=self.menu, data=nested_form_data(raw_data))
        self.assertTrue(form.is_valid(), msg=form.errors.as_json())

    def test_clean_highlights_duplicate_page(self):
        """Checks that the same page used twice in highlights raises an error."""
        page = ThemePageFactory()

        raw_data = self.raw_form_data(
            highlights_data=[
                (
                    "highlight",
                    {
                        "page": page.pk,
                        "external_url": "",
                        "description": "Highlight 1",
                    },
                ),
                (
                    "highlight",
                    {
                        "page": page.pk,
                        "external_url": "",
                        "description": "Highlight 2",
                    },
                ),
            ]
        )

        form = self.form_class(instance=self.menu, data=nested_form_data(raw_data))
        self.assertFalse(form.is_valid())

        self.assertIn("highlights", form.errors)
        print("Form errors", form.errors["highlights"][0])
        self.assertIn("Duplicate page. Please choose a different one.", form.errors["highlights"][0])

    def test_clean_highlights_duplicate_external_url(self):
        """Checks that the same external URL used twice in highlights raises an error."""
        url = "https://example.com"

        raw_data = self.raw_form_data(
            highlights_data=[
                (
                    "highlight",
                    {
                        "page": "",
                        "external_url": url,
                        "description": "Highlight 1",
                    },
                ),
                (
                    "highlight",
                    {
                        "page": "",
                        "external_url": url,
                        "description": "Highlight 2",
                    },
                ),
            ]
        )

        form = self.form_class(instance=self.menu, data=nested_form_data(raw_data))
        self.assertFalse(form.is_valid())
        self.assertIn("Duplicate URL. Please add a different one.", str(form.errors["highlights"]))

    def test_clean_columns_no_duplicates(self):
        """Checks that different pages/URLs across columns, sections, and sub-links do not raise errors."""
        page1 = ThemePageFactory()
        page2 = ThemePageFactory()
        topic1 = TopicPageFactory()
        topic2 = TopicPageFactory()

        raw_data = self.raw_form_data(
            columns_data=[
                (
                    "column",
                    {
                        "sections": streamfield(
                            [
                                (
                                    "section",
                                    {
                                        "section_link": {
                                            "page": page1.pk,
                                            "external_url": "",
                                            "title": "Theme Link",
                                        },
                                        "links": streamfield(
                                            [
                                                (
                                                    "topic_link",
                                                    {
                                                        "page": topic1.pk,
                                                        "external_url": "",
                                                        "title": "Topic Link",
                                                    },
                                                )
                                            ]
                                        ),
                                    },
                                )
                            ]
                        ),
                    },
                ),
                (
                    "column",
                    {
                        "sections": streamfield(
                            [
                                (
                                    "section",
                                    {
                                        "section_link": {
                                            "page": page2.pk,
                                            "external_url": "",
                                            "title": "Theme Link2",
                                        },
                                        "links": streamfield(
                                            [
                                                (
                                                    "topic_link",
                                                    {
                                                        "page": topic2.pk,
                                                        "external_url": "",
                                                        "title": "Topic Link2",
                                                    },
                                                )
                                            ]
                                        ),
                                    },
                                )
                            ]
                        ),
                    },
                ),
            ]
        )

        form = self.form_class(instance=self.menu, data=nested_form_data(raw_data))
        self.assertTrue(form.is_valid(), msg=form.errors.as_json())

    def test_clean_columns_duplicate_section_link(self):
        """Checks that using the same page in two different sections (across columns) raises a duplicate error."""
        same_page = ThemePageFactory()
        different_page = TopicPageFactory()

        raw_data = self.raw_form_data(
            columns_data=[
                (
                    "column",
                    {
                        "sections": streamfield(
                            [
                                (
                                    "section",
                                    {
                                        "section_link": {
                                            "page": same_page.pk,
                                            "external_url": "",
                                            "title": "Theme Link1",
                                        },
                                        "links": streamfield(
                                            [
                                                (
                                                    "topic_link",
                                                    {
                                                        "page": different_page.pk,
                                                        "external_url": "",
                                                        "title": "Sub link #1",
                                                    },
                                                )
                                            ]
                                        ),
                                    },
                                )
                            ]
                        ),
                    },
                ),
                (
                    "column",
                    {
                        "sections": streamfield(
                            [
                                (
                                    "section",
                                    {
                                        "section_link": {
                                            "page": same_page.pk,
                                            "external_url": "",
                                            "title": "Theme Link2",
                                        },
                                        "links": streamfield(
                                            [
                                                (
                                                    "topic_link",
                                                    {
                                                        "page": different_page.pk,
                                                        "external_url": "",
                                                        "title": "Sub link #2",
                                                    },
                                                )
                                            ]
                                        ),
                                    },
                                )
                            ]
                        ),
                    },
                ),
            ]
        )

        form = self.form_class(instance=self.menu, data=nested_form_data(raw_data))
        self.assertFalse(form.is_valid())
        self.assertIn("columns", form.errors)
        self.assertIn("Duplicate page in section link.", str(form.errors["columns"]))

    def test_clean_columns_duplicate_sub_link(self):
        """Checks that using the same sub-link page multiple times triggers a duplicate error."""
        page1 = ThemePageFactory()
        page2 = TopicPageFactory()

        raw_data = self.raw_form_data(
            columns_data=[
                (
                    "column",
                    {
                        "sections": streamfield(
                            [
                                (
                                    "section",
                                    {
                                        "section_link": {
                                            "page": page2.pk,
                                            "external_url": "",
                                            "title": "Section Link",
                                        },
                                        "links": streamfield(
                                            [
                                                (
                                                    "topic_link",
                                                    {
                                                        "page": page1.pk,
                                                        "external_url": "",
                                                        "title": "Sub link #1",
                                                    },
                                                ),
                                                (
                                                    "topic_link",
                                                    {
                                                        "page": page1.pk,
                                                        "external_url": "",
                                                        "title": "Sub link #2",
                                                    },
                                                ),
                                            ]
                                        ),
                                    },
                                )
                            ]
                        ),
                    },
                )
            ]
        )

        form = self.form_class(instance=self.menu, data=nested_form_data(raw_data))
        self.assertFalse(form.is_valid())
        self.assertIn("Duplicate page in links.", str(form.errors["columns"]))

    def test_clean_columns_duplicate_across_section_link_and_sub_link(self):
        """Checks that if a section link page is also used in a sub-link (in the same column or a different column),
        it raises a duplicate error.
        """
        page1 = ThemePageFactory()

        raw_data = self.raw_form_data(
            columns_data=[
                (
                    "column",
                    {
                        "sections": streamfield(
                            [
                                (
                                    "section",
                                    {
                                        "section_link": {
                                            "page": page1.pk,
                                            "external_url": "",
                                            "title": "Section Link #1",
                                        },
                                        "links": streamfield(
                                            [
                                                (
                                                    "topic_link",
                                                    {
                                                        "page": page1.pk,
                                                        "external_url": "",
                                                        "title": "Sub link #1",
                                                    },
                                                ),
                                            ]
                                        ),
                                    },
                                )
                            ]
                        ),
                    },
                )
            ]
        )

        form = self.form_class(instance=self.menu, data=nested_form_data(raw_data))
        self.assertFalse(form.is_valid())
        self.assertIn("Duplicate page in links.", str(form.errors["columns"]))
        self.assertIn("Duplicate page in section link.", str(form.errors["columns"]))
