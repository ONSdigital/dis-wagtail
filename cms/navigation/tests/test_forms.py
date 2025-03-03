import uuid

from django.test import TestCase
from wagtail.admin.panels import get_edit_handler
from wagtail.test.utils.form_data import nested_form_data, streamfield

from cms.navigation.models import FooterMenu, MainMenu
from cms.navigation.tests.factories import (
    FooterMenuFactory,
    HighlightsBlockFactory,
    MainMenuFactory,
    ThemePageFactory,
    TopicPageFactory,
)


class BaseMainMenuTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.menu = MainMenuFactory()
        cls.form_class = get_edit_handler(MainMenu).get_form_class()

        cls.theme_example_url_1 = "https://example.com"
        cls.theme_example_url_2 = "https://example2.com"

        cls.topic_example_url_1 = "https://example3.com"
        cls.topic_example_url_2 = "https://example4.com"

        cls.highlights_1 = HighlightsBlockFactory()
        cls.highlights_2 = HighlightsBlockFactory()

        cls.theme_page_1 = ThemePageFactory()
        cls.theme_page_2 = ThemePageFactory()

        cls.topic_page_1 = TopicPageFactory(parent=cls.theme_page_1)
        cls.topic_page_2 = TopicPageFactory(parent=cls.theme_page_2)

    def raw_form_data(self, highlights_data=None, columns_data=None) -> dict:
        highlights_data = highlights_data or []
        columns_data = columns_data or []

        return {
            "highlights": streamfield(highlights_data),
            "columns": streamfield(columns_data),
        }

    def create_topic(self, topic_page_pk, topic_title, external_url="", order=0):
        return {
            "id": uuid.uuid4(),
            "type": "item",
            "value": {
                "page": topic_page_pk,
                "external_url": external_url,
                "title": topic_title,
            },
            "deleted": "",
            "order": str(order),
        }

    def create_section(self, theme_page_pk, theme_title, external_url="", links=None):
        return {
            "section_link": {
                "page": theme_page_pk,
                "external_url": external_url,
                "title": theme_title,
            },
            "links": links if links else [],
            "links-count": len(links) if links else 0,
        }

    def create_sections(self, data):
        return streamfield(
            [
                (
                    "section",
                    self.create_section(
                        theme_page_pk=item["theme_page_pk"],
                        theme_title=item["theme_title"],
                        external_url=item.get("theme_external_url", ""),
                        links=[
                            self.create_topic(
                                link["topic_page_pk"], link["topic_title"], link.get("external_url", ""), i
                            )
                            for i, link in enumerate(item["links"])
                        ]
                        if "links" in item
                        else None,
                    ),
                )
                for item in data
            ]
        )


class HighlightTests(BaseMainMenuTestCase):
    def test_highlights_no_duplicate_page(self):
        """Checks that different pages in the highlights do not trigger any validation errors."""
        raw_data = self.raw_form_data(
            highlights_data=[
                (
                    "highlight",
                    HighlightsBlockFactory(page=self.theme_page_1.pk, external_url=""),
                ),
                (
                    "highlight",
                    HighlightsBlockFactory(page=self.theme_page_2.pk, external_url=""),
                ),
            ]
        )

        form = self.form_class(instance=self.menu, data=nested_form_data(raw_data))
        self.assertTrue(form.is_valid(), msg=form.errors.as_json())

    def test_highlights_no_duplicate_external_url(self):
        """Checks that the different external URLs used do not trigger any
        validation errors.
        """
        raw_data = self.raw_form_data(
            highlights_data=[
                ("highlight", self.highlights_1),
                ("highlight", self.highlights_2),
            ]
        )

        form = self.form_class(instance=self.menu, data=nested_form_data(raw_data))
        self.assertTrue(form.is_valid(), msg=form.errors.as_json())

    def test_highlights_duplicate_page(self):
        """Checks that the same page used twice in highlights raises an error."""
        highlight = HighlightsBlockFactory(page=self.theme_page_1.pk, external_url="")

        raw_data = self.raw_form_data(
            highlights_data=[
                ("highlight", highlight),
                ("highlight", highlight),
            ]
        )

        form = self.form_class(instance=self.menu, data=nested_form_data(raw_data))
        self.assertFalse(form.is_valid())

        self.assertEqual(
            form.errors["highlights"].data[0].block_errors[1].block_errors["page"].message,
            "Duplicate page. Please choose a different one.",
        )

    def test_highlights_duplicate_external_url(self):
        """Checks that the same external URL used twice in highlights raises an error."""
        raw_data = self.raw_form_data(
            highlights_data=[
                ("highlight", self.highlights_1),
                ("highlight", self.highlights_1),
            ]
        )

        form = self.form_class(instance=self.menu, data=nested_form_data(raw_data))
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors["highlights"].data[0].block_errors[1].block_errors["external_url"].message,
            "Duplicate URL. Please add a different one.",
        )


class ColumnTests(BaseMainMenuTestCase):
    def test_columns_no_duplicate_section_page_across_columns(self):
        """Checks that different pages across columns, sections, and topics do not raise errors."""
        section_data = [
            {
                "theme_page_pk": self.theme_page_1.pk,
                "theme_title": "Theme Page #1",
                "theme_external_url": "",
                "links": [
                    {
                        "topic_page_pk": self.topic_page_1.pk,
                        "topic_title": "Topic Page #1",
                        "external_url": "",
                    },
                ],
            },
            {
                "theme_page_pk": self.theme_page_2.pk,
                "theme_title": "Theme Page #2",
                "theme_external_url": "",
                "links": [
                    {
                        "topic_page_pk": self.topic_page_2.pk,
                        "topic_title": "Topic Page #1",
                        "external_url": "",
                    },
                ],
            },
        ]

        sections_1 = self.create_sections([section_data[0]])
        sections_2 = self.create_sections([section_data[1]])

        raw_data = self.raw_form_data(
            columns_data=[
                ("column", {"sections": sections_1}),
                ("column", {"sections": sections_2}),
            ]
        )

        form = self.form_class(instance=self.menu, data=nested_form_data(raw_data))
        self.assertTrue(form.is_valid(), msg=form.errors.as_json())

    def test_columns_no_duplicate_section_external_url_across_columns(self):
        """Checks that different external URLs across columns, sections, and topics do not raise errors."""
        section_data = [
            {
                "theme_page_pk": None,
                "theme_title": "Theme Page #1",
                "theme_external_url": self.theme_example_url_1,
                "links": [],
            },
            {
                "theme_page_pk": None,
                "theme_title": "Theme Page #2",
                "theme_external_url": self.theme_example_url_2,
                "links": [],
            },
        ]

        sections_1 = self.create_sections([section_data[0]])
        sections_2 = self.create_sections([section_data[1]])

        raw_data = self.raw_form_data(
            columns_data=[
                ("column", {"sections": sections_1}),
                ("column", {"sections": sections_2}),
            ]
        )

        form = self.form_class(instance=self.menu, data=nested_form_data(raw_data))
        self.assertTrue(form.is_valid(), msg=form.errors.as_json())

    def test_columns_duplicate_section_page_across_columns(self):
        """Checks that using the same section page in two different sections
        (across columns) raises a duplicate error.
        """
        section_data = [
            {
                "theme_page_pk": self.theme_page_1.pk,
                "theme_title": "Theme Page #1",
                "theme_external_url": "",
                "links": [],
            }
        ]

        sections = self.create_sections(section_data)

        raw_data = self.raw_form_data(
            columns_data=[
                ("column", {"sections": sections}),
                ("column", {"sections": sections}),
            ]
        )

        form = self.form_class(instance=self.menu, data=nested_form_data(raw_data))
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors["columns"]
            .data[0]
            .block_errors[1]
            .block_errors["sections"]
            .block_errors[0]
            .block_errors["section_link"]
            .message,
            "Duplicate page. Please choose a different one.",
        )

    def test_columns_duplicate_section_external_url_across_columns(self):
        """Checks that using the same external URL in two different sections
        (across columns) raises a duplicate error.
        """
        section_data = [
            {
                "theme_page_pk": None,
                "theme_title": "Theme Page #1",
                "theme_external_url": self.theme_example_url_1,
                "links": [],
            }
        ]

        sections = self.create_sections(section_data)

        raw_data = self.raw_form_data(
            columns_data=[
                ("column", {"sections": sections}),
                ("column", {"sections": sections}),
            ]
        )

        form = self.form_class(instance=self.menu, data=nested_form_data(raw_data))
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors["columns"]
            .data[0]
            .block_errors[1]
            .block_errors["sections"]
            .block_errors[0]
            .block_errors["section_link"]
            .message,
            "Duplicate URL. Please add a different one.",
        )


class TopicTests(BaseMainMenuTestCase):
    def test_columns_no_duplicate_topic_page_across_columns(self):
        """Checks that different topic pages across columns do not raise errors."""
        section_data = [
            {
                "theme_page_pk": self.theme_page_1.pk,
                "theme_title": "Theme Page #1",
                "theme_external_url": "",
                "links": [
                    {
                        "topic_page_pk": self.topic_page_1.pk,
                        "topic_title": "Topic Page #1",
                        "external_url": "",
                    },
                ],
            },
            {
                "theme_page_pk": self.theme_page_2.pk,
                "theme_title": "Theme Page #2",
                "theme_external_url": "",
                "links": [
                    {
                        "topic_page_pk": self.topic_page_2.pk,
                        "topic_title": "Topic Page #2",
                        "external_url": "",
                    },
                ],
            },
        ]

        sections_1 = self.create_sections([section_data[0]])
        sections_2 = self.create_sections([section_data[1]])

        raw_data = self.raw_form_data(
            columns_data=[
                ("column", {"sections": sections_1}),
                ("column", {"sections": sections_2}),
            ]
        )

        form = self.form_class(instance=self.menu, data=nested_form_data(raw_data))
        self.assertTrue(form.is_valid(), msg=form.errors.as_json())

    def test_columns_no_duplicate_topic_external_url_across_columns(self):
        """Checks that different external URLs across columns do not raise errors."""
        section_data = [
            {
                "theme_page_pk": self.theme_page_1.pk,
                "theme_title": "Theme Page #1",
                "theme_external_url": "",
                "links": [
                    {
                        "topic_page_pk": None,
                        "topic_title": "Topic Page #1",
                        "external_url": self.topic_example_url_1,
                    },
                ],
            },
            {
                "theme_page_pk": self.theme_page_2.pk,
                "theme_title": "Theme Page #2",
                "theme_external_url": "",
                "links": [
                    {
                        "topic_page_pk": None,
                        "topic_title": "Topic Page #2",
                        "external_url": self.topic_example_url_2,
                    },
                ],
            },
        ]

        sections_1 = self.create_sections([section_data[0]])
        sections_2 = self.create_sections([section_data[1]])

        raw_data = self.raw_form_data(
            columns_data=[
                ("column", {"sections": sections_1}),
                ("column", {"sections": sections_2}),
            ]
        )

        form = self.form_class(instance=self.menu, data=nested_form_data(raw_data))
        self.assertTrue(form.is_valid(), msg=form.errors.as_json())

    def test_columns_duplicate_topic_page_across_columns(self):
        """Checks that using the same topic page in two different columns raises a duplicate error."""
        section_data = [
            {
                "theme_page_pk": self.theme_page_1.pk,
                "theme_title": "Theme Page #1",
                "theme_external_url": "",
                "links": [
                    {
                        "topic_page_pk": self.topic_page_2.pk,
                        "topic_title": "Topic Page #2",
                        "external_url": "",
                    },
                ],
            },
            {
                "theme_page_pk": self.theme_page_2.pk,
                "theme_title": "Theme Page #2",
                "theme_external_url": "",
                "links": [
                    {
                        "topic_page_pk": self.topic_page_2.pk,
                        "topic_title": "Topic Page #2",
                        "external_url": "",
                    },
                ],
            },
        ]

        sections_1 = self.create_sections([section_data[0]])
        sections_2 = self.create_sections([section_data[1]])

        raw_data = self.raw_form_data(
            columns_data=[
                ("column", {"sections": sections_1}),
                ("column", {"sections": sections_2}),
            ]
        )

        form = self.form_class(instance=self.menu, data=nested_form_data(raw_data))
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors["columns"]
            .data[0]
            .block_errors[1]
            .block_errors["sections"]
            .block_errors[0]
            .block_errors["links"]
            .block_errors[0]
            .block_errors["page"]
            .message,
            "Duplicate page. Please choose a different one.",
        )

    def test_columns_duplicate_topic_external_url_across_columns(self):
        """Checks that using the same external URL in two different columns raises a duplicate error."""
        section_data = [
            {
                "theme_page_pk": self.theme_page_1.pk,
                "theme_title": "Theme Page #1",
                "theme_external_url": "",
                "links": [
                    {
                        "topic_page_pk": None,
                        "topic_title": "Topic Page #1",
                        "external_url": self.topic_example_url_1,
                    },
                ],
            },
            {
                "theme_page_pk": self.theme_page_2.pk,
                "theme_title": "Theme Page #2",
                "theme_external_url": "",
                "links": [
                    {
                        "topic_page_pk": None,
                        "topic_title": "Topic Page #2",
                        "external_url": self.topic_example_url_1,
                    },
                ],
            },
        ]

        sections_1 = self.create_sections([section_data[0]])
        sections_2 = self.create_sections([section_data[1]])

        raw_data = self.raw_form_data(
            columns_data=[
                ("column", {"sections": sections_1}),
                ("column", {"sections": sections_2}),
            ]
        )

        form = self.form_class(instance=self.menu, data=nested_form_data(raw_data))
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors["columns"]
            .data[0]
            .block_errors[1]
            .block_errors["sections"]
            .block_errors[0]
            .block_errors["links"]
            .block_errors[0]
            .block_errors["external_url"]
            .message,
            "Duplicate URL. Please add a different one.",
        )

    def test_columns_no_duplicate_section_page(self):
        """Checks that different section pages within the same column do not raise errors."""
        section_data = [
            {
                "theme_page_pk": self.theme_page_1.pk,
                "theme_title": "Theme Page #1",
                "theme_external_url": "",
                "links": [],
            },
            {
                "theme_page_pk": self.theme_page_2.pk,
                "theme_title": "Theme Page #2",
                "theme_external_url": "",
                "links": [],
            },
        ]

        sections = self.create_sections(section_data)

        raw_data = self.raw_form_data(
            columns_data=[
                ("column", {"sections": sections}),
            ]
        )

        form = self.form_class(instance=self.menu, data=nested_form_data(raw_data))
        self.assertTrue(form.is_valid(), msg=form.errors.as_json())

    def test_columns_no_duplicate_section_external_url(self):
        """Checks that different external URLs within the same column do not raise errors."""
        section_data = [
            {
                "theme_page_pk": None,
                "theme_title": "Theme Page #1",
                "theme_external_url": self.theme_example_url_1,
                "links": [],
            },
            {
                "theme_page_pk": None,
                "theme_title": "Theme Page #2",
                "theme_external_url": self.theme_example_url_2,
                "links": [],
            },
        ]

        sections = self.create_sections(section_data)

        raw_data = self.raw_form_data(
            columns_data=[
                ("column", {"sections": sections}),
            ]
        )

        form = self.form_class(instance=self.menu, data=nested_form_data(raw_data))
        self.assertTrue(form.is_valid(), msg=form.errors.as_json())

    def test_columns_duplicate_section_page(self):
        """Checks that using the same section page in the same column raises a duplicate error."""
        section_data = [
            {
                "theme_page_pk": self.theme_page_1.pk,
                "theme_title": "Theme Page #1",
                "theme_external_url": "",
                "links": [],
            },
            {
                "theme_page_pk": self.theme_page_1.pk,
                "theme_title": "Theme Page #1",
                "theme_external_url": "",
                "links": [],
            },
        ]

        sections = self.create_sections(section_data)

        raw_data = self.raw_form_data(
            columns_data=[
                ("column", {"sections": sections}),
            ]
        )

        form = self.form_class(instance=self.menu, data=nested_form_data(raw_data))
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors["columns"]
            .data[0]
            .block_errors[0]
            .block_errors["sections"]
            .block_errors[1]
            .block_errors["section_link"]
            .message,
            "Duplicate page. Please choose a different one.",
        )

    def test_columns_duplicate_section_external_url(self):
        """Checks that using the same external URL in the same section raises a duplicate error."""
        section_data = [
            {
                "theme_page_pk": None,
                "theme_title": "Theme Page #1",
                "theme_external_url": self.theme_example_url_1,
                "links": [],
            },
            {
                "theme_page_pk": None,
                "theme_title": "Theme Page #1",
                "theme_external_url": self.theme_example_url_1,
                "links": [],
            },
        ]

        sections = self.create_sections(section_data)

        raw_data = self.raw_form_data(
            columns_data=[
                ("column", {"sections": sections}),
            ]
        )

        form = self.form_class(instance=self.menu, data=nested_form_data(raw_data))
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors["columns"]
            .data[0]
            .block_errors[0]
            .block_errors["sections"]
            .block_errors[1]
            .block_errors["section_link"]
            .message,
            "Duplicate URL. Please add a different one.",
        )

    def test_columns_no_duplicate_topics(self):
        """Checks that different topics within the same section do not raise errors."""
        section_data = [
            {
                "theme_page_pk": self.theme_page_1.pk,
                "theme_title": "Theme Page #1",
                "theme_external_url": "",
                "links": [
                    {
                        "topic_page_pk": self.topic_page_1.pk,
                        "topic_title": "Topic Page #1",
                        "external_url": "",
                    },
                    {
                        "topic_page_pk": self.topic_page_2.pk,
                        "topic_title": "Topic Page #2",
                        "external_url": "",
                    },
                ],
            }
        ]

        sections = self.create_sections(section_data)

        raw_data = self.raw_form_data(
            columns_data=[
                ("column", {"sections": sections}),
            ]
        )

        form = self.form_class(instance=self.menu, data=nested_form_data(raw_data))
        self.assertTrue(form.is_valid(), msg=form.errors.as_json())

    def test_columns_no_duplicate_topics_external_url(self):
        """Checks that different external URLs within the same section do not raise errors."""
        section_data = [
            {
                "theme_page_pk": self.theme_page_1.pk,
                "theme_title": "Theme Page #1",
                "theme_external_url": "",
                "links": [
                    {
                        "topic_page_pk": None,
                        "topic_title": "Topic Page #1",
                        "external_url": self.topic_example_url_1,
                    },
                    {
                        "topic_page_pk": None,
                        "topic_title": "Topic Page #2",
                        "external_url": self.topic_example_url_2,
                    },
                ],
            }
        ]

        sections = self.create_sections(section_data)

        raw_data = self.raw_form_data(
            columns_data=[
                ("column", {"sections": sections}),
            ]
        )

        form = self.form_class(instance=self.menu, data=nested_form_data(raw_data))
        self.assertTrue(form.is_valid(), msg=form.errors.as_json())

    def test_columns_duplicate_topics(self):
        """Checks that using the same topic page multiple times within the same section triggers a duplicate error."""
        section_data = [
            {
                "theme_page_pk": self.theme_page_1.pk,
                "theme_title": "Section Page #1",
                "theme_external_url": "",
                "links": [
                    {
                        "topic_page_pk": self.topic_page_1.pk,
                        "topic_title": "Topic Page #1",
                        "external_url": "",
                    },
                    {
                        "topic_page_pk": self.topic_page_1.pk,
                        "topic_title": "Topic Page #2",
                        "external_url": "",
                    },
                ],
            }
        ]

        sections = self.create_sections(section_data)

        raw_data = self.raw_form_data(
            columns_data=[
                ("column", {"sections": sections}),
            ]
        )

        form = self.form_class(instance=self.menu, data=nested_form_data(raw_data))
        self.assertFalse(form.is_valid())

        self.assertEqual(
            form.errors["columns"]
            .data[0]
            .block_errors[0]
            .block_errors["sections"]
            .block_errors[0]
            .block_errors["links"]
            .block_errors[1]
            .block_errors["page"]
            .message,
            "Duplicate page. Please choose a different one.",
        )

    def test_columns_duplicate_topics_external_url(self):
        """Checks that using the same external URL multiple times within the same section triggers a duplicate error."""
        section_data = [
            {
                "theme_page_pk": self.theme_page_1.pk,
                "theme_title": "Section Page #1",
                "theme_external_url": "",
                "links": [
                    {
                        "topic_page_pk": None,
                        "topic_title": "Topic Page #1",
                        "external_url": self.topic_example_url_1,
                    },
                    {
                        "topic_page_pk": None,
                        "topic_title": "Topic Page #2",
                        "external_url": self.topic_example_url_1,
                    },
                ],
            }
        ]

        sections = self.create_sections(section_data)

        raw_data = self.raw_form_data(
            columns_data=[
                ("column", {"sections": sections}),
            ]
        )

        form = self.form_class(instance=self.menu, data=nested_form_data(raw_data))
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors["columns"]
            .data[0]
            .block_errors[0]
            .block_errors["sections"]
            .block_errors[0]
            .block_errors["links"]
            .block_errors[1]
            .block_errors["external_url"]
            .message,
            "Duplicate URL. Please add a different one.",
        )


class FooterMenuNoHelpersTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.footer_menu = FooterMenuFactory()
        cls.form_class = get_edit_handler(FooterMenu).get_form_class()

    def test_no_duplicate_urls_across_columns(self):
        """Ensures that two columns having different external URLs do not trigger
        the duplicate URL validation error.
        """
        # Manually build the POST data for the columns StreamField
        raw_data = {
            "columns": streamfield(
                [
                    (
                        "column",
                        {
                            "title": "Column 1",
                            "links": [
                                {
                                    "id": str(uuid.uuid4()),
                                    "type": "item",
                                    "value": {
                                        "page": "",
                                        "external_url": "https://footer-example-1.com",
                                        "title": "Link #1",
                                    },
                                    "deleted": "",
                                    "order": "0",
                                },
                                {
                                    "id": str(uuid.uuid4()),
                                    "type": "item",
                                    "value": {
                                        "page": "",
                                        "external_url": "https://footer-example-3.com",
                                        "title": "Link #3",
                                    },
                                    "deleted": "",
                                    "order": "1",
                                },
                            ],
                            "links-count": 2,
                        },
                    ),
                    (
                        "column",
                        {
                            "title": "Column 2",
                            "links": [
                                {
                                    "id": str(uuid.uuid4()),
                                    "type": "item",
                                    "value": {
                                        "page": "",
                                        "external_url": "https://footer-example-2.com",
                                        "title": "Link #2",
                                    },
                                    "deleted": "",
                                    "order": "0",
                                }
                            ],
                            "links-count": 1,
                        },
                    ),
                ]
            )
        }

        # Submission of the form
        form = self.form_class(
            instance=self.footer_menu,
            data=nested_form_data(raw_data),
        )
        # We expect no duplicates, so form should be valid
        self.assertTrue(form.is_valid(), msg=form.errors.as_json())

    def test_duplicate_urls_across_column(self):
        """Checks that using the same external URLs in the different columns raises a duplicate error."""
        raw_data = {
            "columns": streamfield(
                [
                    (
                        "column",
                        {
                            "title": "Column 1",
                            "links": [
                                {
                                    "id": str(uuid.uuid4()),
                                    "type": "item",
                                    "value": {
                                        "page": "",
                                        "external_url": "https://footer-example-1.com",
                                        "title": "Link #1",
                                    },
                                    "deleted": "",
                                    "order": "0",
                                },
                                {
                                    "id": str(uuid.uuid4()),
                                    "type": "item",
                                    "value": {
                                        "page": "",
                                        "external_url": "https://footer-example-2.com",
                                        "title": "Link #2",
                                    },
                                    "deleted": "",
                                    "order": "1",
                                },
                            ],
                            "links-count": 2,
                        },
                    ),
                    (
                        "column",
                        {
                            "title": "Column 2",
                            "links": [
                                {
                                    "id": str(uuid.uuid4()),
                                    "type": "item",
                                    "value": {
                                        "page": "",
                                        "external_url": "https://footer-example-2.com",
                                        "title": "Link #2",
                                    },
                                    "deleted": "",
                                    "order": "0",
                                }
                            ],
                            "links-count": 1,
                        },
                    ),
                ]
            )
        }

        form = self.form_class(
            instance=self.footer_menu,
            data=nested_form_data(raw_data),
        )
        self.assertFalse(form.is_valid(), msg=form.errors.as_json())
