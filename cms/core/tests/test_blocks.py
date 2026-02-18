# pylint: disable=too-many-lines
import uuid
from datetime import datetime
from http import HTTPStatus
from unittest.mock import Mock
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from django.template.defaultfilters import filesizeformat
from django.test import TestCase
from wagtail.blocks import StreamBlockValidationError, StructBlockValidationError
from wagtail.images import get_image_model
from wagtail.images.tests.utils import get_test_image_file
from wagtail.rich_text import RichText
from wagtail.test.utils import WagtailPageTestCase
from wagtail.test.utils.wagtail_tests import WagtailTestUtils

from cms.articles.tests.factories import StatisticalArticlePageFactory
from cms.core.blocks import (
    AccordionBlock,
    AccordionSectionBlock,
    BasicTableBlock,
    DocumentBlock,
    DocumentsBlock,
    HeadingBlock,
    ONSTableBlock,
    RelatedContentBlock,
    RelatedLinksBlock,
)
from cms.core.blocks.definitions import DefinitionsBlock
from cms.core.tests.factories import DefinitionFactory
from cms.core.tests.utils import get_test_document
from cms.home.models import HomePage
from cms.standard_pages.models import InformationPage


class CoreBlocksTestCase(TestCase):
    """Test for core blocks."""

    @classmethod
    def setUpTestData(cls):
        cls.home_page = HomePage.objects.first()
        cls.document = get_test_document()

    def test_document_block__block_value(self):
        """Test DocumentBlockStructValue as_macro_data."""
        block = DocumentBlock()
        value = block.to_python(
            {"document": self.document.pk, "title": "The block document", "description": "Document description"}
        )

        self.assertDictEqual(
            value.as_macro_data(),
            {
                "thumbnail": False,
                "title": {
                    "text": "The block document",
                    "url": self.document.url,
                },
                "description": RichText("Document description"),
                "metadata": {
                    "file": {
                        "fileType": "TXT",
                        "fileSize": "25\xa0bytes",
                    }
                },
                "attributes": {
                    "data-ga-event": "file-download",
                    "data-ga-file-extension": self.document.file_extension.lower(),
                    "data-ga-file-name": self.document.title,
                    "data-ga-link-text": "The block document",
                    "data-ga-link-url": self.document.url,
                    "data-ga-link-domain": urlparse(self.document.url).hostname,
                    "data-ga-file-size": "0.025",  # KB
                },
            },
        )

    def test_documents_block__get_context(self):
        """Tests the macro data in context."""
        block = DocumentsBlock()
        value = block.to_python(
            [
                {
                    "type": "document",
                    "value": {
                        "document": self.document.pk,
                        "title": "The block document",
                        "description": "Document description",
                    },
                }
            ]
        )

        context = block.get_context(value)
        self.assertListEqual(
            context["macro_data"],
            [
                {
                    "thumbnail": False,
                    "title": {
                        "text": "The block document",
                        "url": self.document.url,
                    },
                    "description": RichText("Document description"),
                    "metadata": {
                        "file": {
                            "fileType": "TXT",
                            "fileSize": "25\xa0bytes",
                        }
                    },
                    "attributes": {
                        "data-ga-event": "file-download",
                        "data-ga-file-extension": self.document.file_extension.lower(),
                        "data-ga-file-name": self.document.title,
                        "data-ga-link-text": "The block document",
                        "data-ga-link-url": self.document.url,
                        "data-ga-link-domain": urlparse(self.document.url).hostname,
                        "data-ga-file-size": "0.025",  # KB
                    },
                }
            ],
        )

    def test_headingblock__get_context(self):
        """Checks that the headingblock context has the TOC."""
        for show_back_to_toc in [None, False, True]:
            with self.subTest(show_back_to_toc=show_back_to_toc):
                block = HeadingBlock(show_back_to_toc=show_back_to_toc)
                value = block.to_python("The Heading")
                self.assertEqual(block.get_context(value)["show_back_to_toc"], show_back_to_toc)

    def test_headingblock__toc(self):
        """Checks the headingblock TOC."""
        block = HeadingBlock()

        self.assertListEqual(
            block.to_table_of_contents_items(block.to_python("The Heading")),
            [
                {
                    "url": "#the-heading",
                    "text": "The Heading",
                    "attributes": {
                        "data-ga-event": "navigation-onpage",
                        "data-ga-navigation-type": "table-of-contents",
                        "data-ga-section-title": "The Heading",
                    },
                }
            ],
        )

    def test_relatedcontentblock_clean__no_page_nor_url(self):
        """Checks that the RelatedContentBlock validates that one of page or URL is supplied."""
        block = RelatedContentBlock()
        value = block.to_python({})

        with self.assertRaises(StreamBlockValidationError) as info:
            block.clean(value)

        self.assertEqual(info.exception.block_errors["page"].message, "Either Page or External Link is required.")
        self.assertEqual(
            info.exception.block_errors["external_url"].message, "Either Page or External Link is required."
        )

    def test_relatedcontentblock_clean__page_and_url(self):
        """Checks that the RelatedContentBlock validates either page or URL is supplied."""
        block = RelatedContentBlock()
        value = block.to_python(
            {
                "page": 1,
                "external_url": "https://ons.gov.uk",
            }
        )

        with self.assertRaises(StreamBlockValidationError) as info:
            block.clean(value)

        self.assertEqual(info.exception.block_errors["page"].message, "Please select either a page or a URL, not both.")
        self.assertEqual(
            info.exception.block_errors["external_url"].message, "Please select either a page or a URL, not both."
        )

    def test_relatedcontentblock_clean__url_no_title(self):
        """Checks that the title is supplied if checking an external url."""
        block = RelatedContentBlock()
        value = block.to_python(
            {
                "external_url": "https://ons.gov.uk",
            }
        )

        with self.assertRaises(StreamBlockValidationError) as info:
            block.clean(value)

        self.assertEqual(info.exception.block_errors["title"].message, "Title is required for external links.")

    def test_relatedcontentblock_clean__url_no_content_type(self):
        """Checks that the content type is supplied if checking an external url."""
        block = RelatedContentBlock()
        value = block.to_python(
            {
                "external_url": "https://ons.gov.uk",
                "title": "Example",
            }
        )

        with self.assertRaises(StructBlockValidationError) as info:
            block.clean(value)

        self.assertEqual(
            info.exception.block_errors["content_type"].message,
            "You must select a content type when providing an external URL.",
        )

    def test_relatedcontentblock_clean__happy_path(self):
        """Happy path for the RelatedContentBlock validation."""
        block = RelatedContentBlock()
        value = block.to_python(
            {"external_url": "https://ons.gov.uk", "title": "The link", "description": "", "content_type": "ARTICLE"}
        )

        self.assertEqual(block.clean(value), value)

    def test_relatedcontentblock_clean__link_value(self):
        """Checks the RelatedContentValue link value."""
        block = RelatedContentBlock()

        value = block.to_python({})
        self.assertIsNone(value.get_link())

        value = block.to_python(
            {
                "external_url": "https://ons.gov.uk",
                "title": "Example",
                "description": "A link",
                "content_type": "ARTICLE",
            }
        )

        self.assertDictEqual(
            value.get_link(),
            {
                "url": "https://ons.gov.uk",
                "text": "Example",
                "description": "A link",
                "metadata": {"object": {"text": "Article"}},
            },
        )

        value = block.to_python(
            {
                "page": self.home_page.pk,
                "title": "Example",
                "description": "A link",
            }
        )

        self.assertDictEqual(
            value.get_link(),
            {
                "url": self.home_page.url,
                "text": "Example",
                "description": "A link",
                "metadata": {"object": {"text": "Page"}},
            },
        )

        value = block.to_python(
            {
                "page": self.home_page.pk,
            }
        )

        self.assertDictEqual(
            value.get_link(),
            {
                "url": self.home_page.url,
                "text": self.home_page.title,
                "description": "",
                "metadata": {"object": {"text": "Page"}},
            },
        )

        statistical_article = StatisticalArticlePageFactory(
            release_date=datetime(2023, 10, 1), summary="Our test description"
        )

        value = block.to_python(
            {
                "page": statistical_article.pk,
            }
        )

        self.assertDictEqual(
            value.get_link(),
            {
                "url": statistical_article.url,
                "text": statistical_article.display_title,
                "description": "Our test description",
                "metadata": {
                    "date": {
                        "iso": "2023-10-01",
                        "prefix": "Released",
                        "short": "1 October 2023",
                        "showPrefix": True,
                    },
                    "object": {"text": "Article"},
                },
            },
        )

    def test_relatedcontentblock_clean__link_value_get_related_link(self):
        """Checks the RelatedContentValue link value."""
        block = RelatedContentBlock()

        value = block.to_python({})
        self.assertIsNone(value.get_related_link())

        value = block.to_python(
            {
                "external_url": "https://ons.gov.uk",
                "title": "Example 1",
                "description": "A link",
                "content_type": "ARTICLE",
            }
        )

        self.assertDictEqual(
            value.get_related_link(),
            {
                "title": {"url": "https://ons.gov.uk", "text": "Example 1"},
                "description": "A link",
                "metadata": {"object": {"text": "Article"}},
                "attributes": {
                    "data-ga-event": "navigation-click",
                    "data-ga-link-text": "Example 1",
                    "data-ga-navigation-type": "links-within-content",
                },
            },
        )

        value = block.to_python(
            {
                "page": self.home_page.pk,
                "title": "Example 2",
                "description": "A link",
                "content_type": "TIME_SERIES",
            }
        )

        self.assertDictEqual(
            value.get_related_link(),
            {
                "title": {"url": self.home_page.url, "text": "Example 2"},
                "description": "A link",
                "metadata": {"object": {"text": "Time series"}},
                "attributes": {
                    "data-ga-event": "navigation-click",
                    "data-ga-link-text": "Example 2",
                    "data-ga-navigation-type": "links-within-content",
                    "data-ga-click-path": "/",
                    "data-ga-click-content-type": "homepage",
                },
            },
        )

        value = block.to_python(
            {
                "page": self.home_page.pk,
                "content_type": "DATASET",
            }
        )

        self.assertDictEqual(
            value.get_related_link(),
            {
                "title": {"url": self.home_page.url, "text": self.home_page.title},
                "metadata": {"object": {"text": "Dataset"}},
                "attributes": {
                    "data-ga-event": "navigation-click",
                    "data-ga-link-text": self.home_page.title,
                    "data-ga-navigation-type": "links-within-content",
                    "data-ga-click-path": "/",
                    "data-ga-click-content-type": "homepage",
                },
            },
        )

    def test_relatedlinksblock__get_context(self):
        """Check that RelatedLinksBlock heading and slug are in the context."""
        block = RelatedLinksBlock(add_heading=True)
        value = block.to_python(
            [
                {
                    "external_url": "https://ons.gov.uk",
                    "title": "Example",
                    "description": "A link",
                    "content_type": "ARTICLE",
                }
            ]
        )

        context = block.get_context(value)
        self.assertEqual(context["heading"], "Related links")
        self.assertEqual(context["slug"], "related-links")
        self.assertEqual(
            context["related_links"],
            [
                {
                    "title": {"url": "https://ons.gov.uk", "text": "Example"},
                    "description": "A link",
                    "metadata": {"object": {"text": "Article"}},
                    "attributes": {
                        "data-ga-click-position": 1,
                        "data-ga-event": "navigation-click",
                        "data-ga-link-text": "Example",
                        "data-ga-navigation-type": "links-within-content",
                        "data-ga-section-title": "Related links",
                    },
                },
            ],
        )

        block_no_heading = RelatedLinksBlock()

        context = block_no_heading.get_context(value)

        self.assertNotIn("heading", context)
        self.assertNotIn("slug", context)
        self.assertIn("related_links", context)

    def test_relatedlinksblock__toc(self):
        """Check the RelatedLinksBlock TOC."""
        block = RelatedLinksBlock(add_heading=True)
        self.assertEqual(
            block.to_table_of_contents_items(block.to_python([])), [{"url": "#related-links", "text": "Related links"}]
        )

    def test_relatedlinksblock__internal_article_link_attributes(self):
        article_page = StatisticalArticlePageFactory()

        block = RelatedLinksBlock(add_heading=True)
        value = block.to_python(
            [
                {
                    "page": article_page.pk,
                }
            ]
        )
        context = block.get_context(value)

        related_links = context["related_links"]
        self.assertEqual(len(related_links), 1)
        related_link = related_links[0]
        self.assertIn("attributes", related_link)

        # Attribute on all links
        self.assertEqual(related_link["attributes"]["data-ga-section-title"], block.heading)
        self.assertEqual(related_link["attributes"]["data-ga-event"], "navigation-click")
        self.assertEqual(related_link["attributes"]["data-ga-link-text"], article_page.display_title)
        self.assertEqual(related_link["attributes"]["data-ga-navigation-type"], "links-within-content")
        self.assertEqual(related_link["attributes"]["data-ga-click-position"], 1)

        # Attributes specific to internal links
        self.assertEqual(related_link["attributes"]["data-ga-click-path"], article_page.get_url())
        self.assertEqual(related_link["attributes"]["data-ga-click-content-type"], article_page.analytics_content_type)
        self.assertEqual(
            related_link["attributes"]["data-ga-click-content-group"], article_page.analytics_content_group
        )
        self.assertEqual(
            related_link["attributes"]["data-ga-click-content-theme"], article_page.analytics_content_theme
        )

        # Attributes specific to articles
        self.assertEqual(
            related_link["attributes"]["data-ga-click-output-series"],
            article_page.cached_analytics_values["outputSeries"],
        )
        self.assertEqual(
            related_link["attributes"]["data-ga-click-output-edition"],
            article_page.cached_analytics_values["outputEdition"],
        )
        self.assertEqual(
            related_link["attributes"]["data-ga-click-release-date"],
            article_page.cached_analytics_values["releaseDate"],
        )

    def test_relatedlinksblock__internal_link_attributes(self):
        block = RelatedLinksBlock(add_heading=True)
        value = block.to_python(
            [
                {
                    "page": self.home_page.pk,
                }
            ]
        )
        context = block.get_context(value)

        related_links = context["related_links"]
        self.assertEqual(len(related_links), 1)
        related_link = related_links[0]
        self.assertIn("attributes", related_link)

        # Attribute on all links
        self.assertEqual(related_link["attributes"]["data-ga-section-title"], block.heading)
        self.assertEqual(related_link["attributes"]["data-ga-event"], "navigation-click")
        self.assertEqual(related_link["attributes"]["data-ga-link-text"], self.home_page.title)
        self.assertEqual(related_link["attributes"]["data-ga-navigation-type"], "links-within-content")
        self.assertEqual(related_link["attributes"]["data-ga-click-position"], 1)

        # Attributes specific to internal links
        self.assertEqual(related_link["attributes"]["data-ga-click-path"], self.home_page.get_url())
        self.assertEqual(
            related_link["attributes"]["data-ga-click-content-type"], self.home_page.analytics_content_type
        )

    def test_relatedlinksblock__external_link_attributes(self):
        block = RelatedLinksBlock(add_heading=True)
        value = block.to_python(
            [
                {
                    "external_url": "https://example.com",
                    "title": "Example",
                    "description": "A link",
                    "content_type": "ARTICLE",
                },
                {
                    "external_url": "https://example.com/2",
                    "title": "Example2",
                    "description": "A second link",
                    "content_type": "ARTICLE",
                },
            ]
        )
        context = block.get_context(value)

        related_links = context["related_links"]
        self.assertEqual(len(related_links), 2)
        related_link = related_links[0]
        self.assertIn("attributes", related_link)

        self.assertEqual(related_link["attributes"]["data-ga-section-title"], block.heading)
        self.assertEqual(related_link["attributes"]["data-ga-event"], "navigation-click")
        self.assertEqual(related_link["attributes"]["data-ga-link-text"], "Example")
        self.assertEqual(related_link["attributes"]["data-ga-navigation-type"], "links-within-content")
        self.assertEqual(related_link["attributes"]["data-ga-click-position"], 1)

        related_link_2 = related_links[1]
        self.assertIn("attributes", related_link_2)
        self.assertEqual(related_link_2["attributes"]["data-ga-click-position"], 2)

    def test_basictableblock__get_context(self):
        """Tests the BasicTableBlock context has DS-compatible options."""
        block = BasicTableBlock()
        value = {
            "first_row_is_table_header": False,
            "first_col_is_header": False,
            "table_caption": "Caption",
            "data": [
                ["Foo", "Bar"],
                ["one", "two"],
            ],
        }

        context = block.get_context(value)
        self.assertDictEqual(
            context["options"],
            {
                "caption": "Caption",
                "ths": [],
                "trs": [
                    {"tds": [{"value": "Foo"}, {"value": "Bar"}]},
                    {"tds": [{"value": "one"}, {"value": "two"}]},
                ],
            },
        )

        value["first_row_is_table_header"] = True
        context = block.get_context(value)
        self.assertDictEqual(
            context["options"],
            {
                "caption": "Caption",
                "ths": [{"value": "Foo"}, {"value": "Bar"}],
                "trs": [{"tds": [{"value": "one"}, {"value": "two"}]}],
            },
        )


class DefinitionsBlockTestCase(TestCase):
    """Test for Definitions block."""

    def test_definitions_block_clean_method_removes_duplicates(self):
        """Test that the clean method of the DefinitionsBlock removes duplicated instances of definitions."""
        term = DefinitionFactory()
        another_term = DefinitionFactory()
        block = DefinitionsBlock()

        value = block.to_python([term.pk, term.pk, another_term.pk])
        clean_value = block.clean(value)

        self.assertEqual(len(clean_value), 2)
        self.assertEqual(clean_value[0].pk, term.pk)
        self.assertEqual(clean_value[1].pk, another_term.pk)

    def test_definitions_block__get_context(self):
        """Test that get_context returns correctly formatted data to be used by the ONS Accordion component."""
        term = DefinitionFactory()
        block = DefinitionsBlock()

        value = block.to_python([term.pk])
        context = block.get_context(value)

        self.assertListEqual(
            context["formatted_definitions"],
            [
                {
                    "headingLevel": 3,
                    "title": term.name,
                    "content": f'<div class="rich-text">{term.definition}</div>',
                }
            ],
        )

    def test_definitions_block__render_uses_definitions_terminology(self):
        """Test that the rendered block uses 'definitions' terminology for accessibility."""
        term = DefinitionFactory()
        block = DefinitionsBlock()

        value = block.to_python([term.pk])
        rendered = block.render(value)

        # Verify aria-labels use 'definitions' not 'glossary'
        self.assertIn('data-open-aria-label="Show all definitions"', rendered)
        self.assertIn('data-close-aria-label="Hide all definitions"', rendered)
        self.assertNotIn("glossary", rendered.lower())


class ONSTableBlockTestCase(WagtailTestUtils, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.simple_table_data = {
            "headers": [[{"value": "header cell", "type": "th"}]],
            "rows": [[{"value": "row cell", "type": "td"}]],
        }
        cls.full_data = {
            "title": "The table",
            "caption": "The caption",
            "source": "https://ons.gov.uk",
            "footnotes": "footnotes",
            "data": cls.simple_table_data,
        }
        cls.data_with_empty_table = {
            "title": "The table",
            "caption": "The caption",
            "source": "https://ons.gov.uk",
            "footnotes": "footnotes",
            "data": {
                "headers": [],
                "rows": [],
            },
        }

        cls.block = ONSTableBlock()

    def test_get_context(self):
        context = self.block.get_context(self.full_data)
        self.assertDictEqual(
            context["options"],
            {
                "caption": "The caption",
                "thList": [{"ths": [{"value": "header cell"}]}],
                "trs": [{"tds": [{"value": "row cell"}]}],
            },
        )
        self.assertEqual(context["title"], "The table")
        self.assertEqual(context["source"], "https://ons.gov.uk")
        self.assertEqual(context["footnotes"], "footnotes")

    def test_get_context__with_empty_table(self):
        context = self.block.get_context(self.data_with_empty_table)
        self.assertNotIn("title", context)
        self.assertNotIn("caption", context)
        self.assertNotIn("options", context)
        self.assertNotIn("source", context)
        self.assertNotIn("footnotes", context)

    def test_render_block__full(self):
        rendered = self.block.render(self.full_data)
        self.assertIn(self.full_data["title"], rendered)
        self.assertIn(self.full_data["caption"], rendered)
        self.assertIn("Footnotes", rendered)
        self.assertIn(self.full_data["footnotes"], rendered)
        self.assertIn("<table", rendered)
        self.assertIn("ons-table", rendered)
        self.assertIn("header cell", rendered)
        self.assertIn("row cell", rendered)

    def test_render_block__no_table(self):
        rendered = self.block.render(self.data_with_empty_table)
        self.assertNotIn(self.full_data["title"], rendered)
        self.assertNotIn(self.full_data["caption"], rendered)
        self.assertNotIn("Footnotes", rendered)
        self.assertNotIn("<table ", rendered)
        self.assertNotIn("header cell", rendered)
        self.assertNotIn("row cell", rendered)

    def test_render_block__optional_elements(self):
        base_value = {"data": self.simple_table_data}

        data = {
            "title": "The table",
            "caption": "The caption",
            "source": "https://ons.gov.uk",
            "footnotes": "footnotes",
        }

        cases = [
            # field with value, fields not rendered
            ("title", ["caption", "source", "footnotes"]),
            ("caption", ["title", "source", "footnotes"]),
            ("source", ["title", "caption", "footnotes"]),
            ("footnotes", ["title", "caption", "source"]),
        ]

        for field_name, not_present in cases:
            with self.subTest(field_name=field_name):
                field_value = data[field_name]
                rendered = self.block.render({**base_value, **{field_name: field_value}})

                self.assertIn("header cell", rendered)
                self.assertIn("row cell", rendered)
                self.assertIn(field_value, rendered)

                for field in not_present:
                    self.assertNotIn(data[field], rendered)

    def test_render_block__alignment_and_width(self):
        table_data = {
            "headers": [[{"value": "header cell", "type": "th", "width": "20px", "align": "center"}]],
            "rows": [[{"value": "row cell", "type": "td", "width": "50%", "align": "right"}]],
        }

        rendered = self.block.render({"data": table_data})

        # Check header cell has alignment class
        self.assertIn("ons-u-ta-center", rendered)
        self.assertIn("header cell", rendered)
        # Check body cell has alignment class
        self.assertIn("ons-u-ta-right", rendered)
        self.assertIn("row cell", rendered)

    def test_render_block__ds_component_markup(self):
        """Test that table renders with correct DS component structure."""
        # Test basic table with body only
        table = {
            "headers": [],
            "rows": [[{"value": "row cell", "type": "td"}]],
        }
        rendered = self.block.render({"data": table})

        # Check key structural elements
        self.assertIn("ons-table-scrollable", rendered)  # DS always adds scrollable wrapper
        self.assertIn("ons-table__body", rendered)
        self.assertIn("ons-table__row", rendered)
        self.assertInHTML('<td class="ons-table__cell">row cell</td>', rendered)

        # Test table with header only
        table = {
            "headers": [[{"value": "header cell", "type": "th"}]],
            "rows": [],
        }
        rendered = self.block.render({"data": table})

        self.assertIn("ons-table__head", rendered)
        self.assertInHTML(
            '<th scope="col" class="ons-table__header"><span class="ons-table__header-text">header cell</span></th>',
            rendered,
        )

        # Test complex table with multiple header rows and row headers
        table = {
            "headers": [
                [
                    {"value": "Combined header", "type": "th", "colspan": 2},
                    {"value": "Regular header", "type": "th"},
                    {"value": "Two row header", "type": "th", "rowspan": 2},
                ],
                [
                    {"value": "Sub-header 1", "type": "th"},
                    {"value": "Sub-header 2", "type": "th"},
                    {"value": "Sub-header 3", "type": "th"},
                ],
            ],
            "rows": [
                [
                    {"value": "Col header 1", "type": "th", "scope": "row"},
                    {"value": "Two rows and cols cell", "type": "td", "rowspan": 2, "colspan": 2},
                    {"value": "Col cell 1", "type": "td"},
                ],
                [
                    {"value": "Col header 2", "type": "th", "scope": "row"},
                    {"value": "Col cell 2", "type": "td", "rowspan": 2},
                ],
                [
                    {"value": "Col header 3", "type": "th", "scope": "row"},
                    {"value": "Col cell 3", "type": "td", "colspan": 3},
                ],
            ],
        }
        rendered = self.block.render({"data": table})

        # Check multiple header rows are rendered
        self.assertIn("Combined header", rendered)
        self.assertIn("Sub-header 1", rendered)
        # Check colspan/rowspan attributes
        self.assertIn('colspan="2"', rendered)
        self.assertIn('rowspan="2"', rendered)
        # Check row headers in body are rendered with heading attribute (th with scope=row)
        self.assertInHTML('<th class="ons-table__cell" scope="row">Col header 1</th>', rendered)
        self.assertInHTML('<th class="ons-table__cell" scope="row">Col header 2</th>', rendered)
        self.assertInHTML('<th class="ons-table__cell" scope="row">Col header 3</th>', rendered)

    def test__align_to_ons_classname(self):
        scenarios = {"right": "ons-u-ta-right", "left": "ons-u-ta-left", "center": "ons-u-ta-center", "foo": ""}
        for alignment, classname in scenarios.items():
            self.assertEqual(
                self.block._align_to_ons_classname(alignment),  # pylint: disable=protected-access
                classname,
            )

    def test__prepare_header_cells(self):
        """Test that header cells are prepared correctly for DS macro."""
        cells = [{"value": "header cell", "type": "th", "width": "20px", "align": "center"}]
        expected = [{"value": "header cell", "width": "20px", "thClasses": "ons-u-ta-center"}]
        self.assertListEqual(
            self.block._prepare_header_cells(cells),  # pylint: disable=protected-access
            expected,
        )

    def test__prepare_body_cells(self):
        """Test that body cells are prepared correctly for DS macro."""
        scenarios = [
            # Regular td cell
            (
                [{"value": "row cell", "type": "td", "width": "50%", "align": "right"}],
                [{"value": "row cell", "width": "50%", "tdClasses": "ons-u-ta-right"}],
            ),
            # Row header (th in body) - should convert to heading=true
            (
                [{"value": "row header", "type": "th", "scope": "row"}],
                [{"value": "row header", "heading": True}],
            ),
        ]
        for cells, expected in scenarios:
            with self.subTest(cells=cells):
                self.assertListEqual(
                    self.block._prepare_body_cells(cells),  # pylint: disable=protected-access
                    expected,
                )

    def test_ons_table_block_includes_download_config_with_context(self):
        """Test that download config is added to options when block_id and page are present."""
        page = StatisticalArticlePageFactory()
        context = {
            "block_id": "test-block-id",
            "page": page,
            "request": None,
        }

        result = self.block.get_context(self.full_data, parent_context=context)

        self.assertIn("options", result)
        self.assertIn("download", result["options"])
        self.assertIn("title", result["options"]["download"])
        self.assertIn("itemsList", result["options"]["download"])
        self.assertEqual(result["options"]["download"]["title"], "Download: The table")
        self.assertEqual(len(result["options"]["download"]["itemsList"]), 1)
        self.assertIn("CSV", result["options"]["download"]["itemsList"][0]["text"])
        self.assertIn("url", result["options"]["download"]["itemsList"][0])

    def test_ons_table_block_builds_preview_url_correctly(self):
        """Test that preview URL is built correctly for draft content."""
        page = StatisticalArticlePageFactory()
        page.latest_revision_id = 123

        request = Mock()
        request.is_preview = True
        request.resolver_match = Mock()
        request.resolver_match.kwargs = {"revision_id": 456}

        context = {
            "block_id": "test-block-id",
            "page": page,
            "request": request,
        }

        result = self.block.get_context(self.full_data, parent_context=context)

        download_url = result["options"]["download"]["itemsList"][0]["url"]
        self.assertIn("/admin/articles/pages/", download_url)
        self.assertIn("/revisions/456/", download_url)
        self.assertIn("/download-table/test-block-id/", download_url)

    def test_ons_table_block_builds_published_url_correctly(self):
        """Test that published URL is built correctly for live content."""
        page = StatisticalArticlePageFactory()
        # Mock the url property since it's read-only
        page_mock = Mock(spec=page)
        page_mock.url = "/economy/articles/test-article/"
        page_mock.pk = page.pk

        context = {
            "block_id": "test-block-id",
            "page": page_mock,
            "request": None,
        }

        result = self.block.get_context(self.full_data, parent_context=context)

        download_url = result["options"]["download"]["itemsList"][0]["url"]
        self.assertEqual(download_url, "/economy/articles/test-article/download-table/test-block-id")

    def test_ons_table_block_download_config_missing_without_page(self):
        """Test that download is empty when page is missing from context."""
        context = {
            "block_id": "test-block-id",
            "page": None,
            "request": None,
        }

        result = self.block.get_context(self.full_data, parent_context=context)

        # download should be empty dict when page is missing
        self.assertEqual(result["options"]["download"], {})


class AccordionBlockTestCase(TestCase):
    """Test for accordion blocks."""

    def setUp(self):
        self.accordion_block = AccordionBlock()
        self.accordion_section_block = AccordionSectionBlock()

    def test_accordion_section_block_structure(self):
        """Test that AccordionSectionBlock has the correct structure."""
        self.assertIn("title", self.accordion_section_block.child_blocks)
        self.assertIn("content", self.accordion_section_block.child_blocks)

        # Test max_length on title
        title_block = self.accordion_section_block.child_blocks["title"]
        self.assertEqual(title_block.field.max_length, 200)

        # Test that both fields are required
        self.assertTrue(title_block.required)
        self.assertTrue(self.accordion_section_block.child_blocks["content"].required)

    def test_accordion_section_block_to_python(self):
        """Test that AccordionSectionBlock can parse data correctly."""
        data = {"title": "Test Section", "content": "This is test content"}

        value = self.accordion_section_block.to_python(data)
        self.assertEqual(value["title"], "Test Section")
        self.assertIn("This is test content", str(value["content"]))

    def test_accordion_block_get_context(self):
        """Test that AccordionBlock generates correct context."""
        test_data = [{"title": "Section 1", "content": "Content 1"}, {"title": "Section 2", "content": "Content 2"}]

        value = self.accordion_block.to_python(test_data)
        context = self.accordion_block.get_context(value)

        # Check that context contains expected keys
        self.assertIn("accordion_sections", context)
        self.assertIn("show_all_text", context)
        self.assertIn("hide_all_text", context)

        # Check accordion_sections structure
        accordion_sections = context["accordion_sections"]
        self.assertEqual(len(accordion_sections), 2)

        # Check first section
        first_section = accordion_sections[0]
        self.assertEqual(first_section["title"], "Section 1")
        self.assertIn("Content 1", str(first_section["content"]))

        # Check second section
        second_section = accordion_sections[1]
        self.assertEqual(second_section["title"], "Section 2")
        self.assertIn("Content 2", str(second_section["content"]))

        # Check button text
        self.assertEqual(context["show_all_text"], "Show all")
        self.assertEqual(context["hide_all_text"], "Hide all")

    def test_accordion_block_render(self):
        """Test that AccordionBlock renders correctly."""
        test_data = [{"title": "Test Section", "content": "Test content"}]

        value = self.accordion_block.to_python(test_data)
        rendered = self.accordion_block.render(value)

        self.assertIn("Test Section", rendered)
        self.assertIn("Test content", rendered)

    def test_accordion_block_empty_list(self):
        """Test AccordionBlock with empty list."""
        value = self.accordion_block.to_python([])
        context = self.accordion_block.get_context(value)

        self.assertEqual(len(context["accordion_sections"]), 0)

    def test_accordion_section_heading_attributes(self):
        """Test that AccordionSectionBlock includes correct attributes for GTM tracking."""
        test_data = [{"title": "Test Section", "content": "Test content"}]
        value = self.accordion_block.to_python(test_data)
        context = self.accordion_block.get_context(value)

        self.assertIn("headingAttributes", context["accordion_sections"][0])
        heading_attributes = context["accordion_sections"][0]["headingAttributes"]
        self.assertEqual(heading_attributes["data-ga-event"], "interaction")
        self.assertEqual(heading_attributes["data-ga-interaction-type"], "accordion")
        self.assertEqual(heading_attributes["data-ga-interaction-label"], "Test Section")
        self.assertEqual(heading_attributes["data-ga-click-position"], 1)


class InformationPageImageBlockRenderingTests(WagtailPageTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.home = HomePage.objects.first()
        image = get_image_model()

        # Create a real CustomImage instance (since WAGTAILIMAGES_IMAGE_MODEL points to it)
        cls.image = image.objects.create(
            title="Test image title",
            file=get_test_image_file(),  # default test.png
            description="Meaningful alt text",
        )

        cls.small = cls.image.get_rendition("width-1024")
        cls.large = cls.image.get_rendition("width-2048")

    def _make_information_page(self, *, download: bool, image=None) -> InformationPage:
        image = image or self.image

        page = InformationPage(
            title="Info page with image",
            summary="<p>Summary</p>",
            content=[
                {
                    "type": "section",
                    "value": {
                        "title": "A section heading",
                        "content": [
                            {
                                "type": "image",
                                "value": {
                                    "image": image.id,
                                    "figure_title": "Figure 1",
                                    "figure_subtitle": "Figure subtitle",
                                    "supporting_text": "Office for National Statistics",
                                    "download": download,
                                },
                                "id": str(uuid.uuid4()),
                            }
                        ],
                    },
                    "id": str(uuid.uuid4()),
                }
            ],
        )
        self.home.add_child(instance=page)
        page.save_revision().publish()

        return page

    def test_renders_small_and_large_renditions_and_alt_text(self):
        page = self._make_information_page(download=False)

        response = self.client.get(page.url)
        self.assertEqual(response.status_code, HTTPStatus.OK)

        # Alt text from CustomImage.description
        self.assertContains(response, 'alt="Meaningful alt text"')

        # onsImage macro outputs src/srcset with both specific rendition URLs
        # Use the underlying file URLs to be agnostic of serve method
        self.assertContains(response, self.small.url)
        self.assertContains(response, self.large.url)

    def test_renders_download_link_with_file_type_and_size_when_enabled(self):
        page = self._make_information_page(download=True)

        response = self.client.get(page.url)
        self.assertEqual(response.status_code, HTTPStatus.OK)

        # Download section rendered
        self.assertContains(response, "Download this image")

        # HTML5 download attribute present once (avoid base-template noise)
        self.assertContains(response, " download", count=1)

        # Large rendition used for download (assert exact URL appears twice in the response)
        # Assert exact downloadable rendition file URL appears twice: once in href, once in onsImage srcset
        self.assertContains(response, self.large.url, count=2)
        self.assertContains(response, self.small.url, count=2)

        # Assert the actual download anchor exists and targets the large rendition URL
        html = response.content.decode(response.charset or "utf-8", errors="replace")
        soup = BeautifulSoup(html, "html.parser")
        download_link = soup.select_one("a[download]")

        self.assertIsNotNone(download_link)
        self.assertEqual(download_link.get("href"), self.large.url)

        expected = filesizeformat(self.large.file.size)
        self.assertIn(f"({expected})", download_link.get_text(strip=True))

    def test_does_not_render_download_link_when_disabled(self):
        page = self._make_information_page(download=False)

        response = self.client.get(page.url)
        self.assertEqual(response.status_code, HTTPStatus.OK)

        # Download section not rendered
        self.assertNotContains(response, "Download this image")

        # No HTML5 download attribute
        self.assertNotContains(response, " download")

        # No anchor with download attribute
        html = response.content.decode(response.charset or "utf-8", errors="replace")
        soup = BeautifulSoup(html, "html.parser")
        download_link = soup.select_one("a[download]")
        self.assertIsNone(download_link)

    def test_renders_when_image_is_missing(self):
        image_model = get_image_model()
        image = image_model.objects.create(
            title="Test image to delete",
            file=get_test_image_file(),
            description="Temporary alt text",
        )

        page = self._make_information_page(download=True, image=image)

        image.delete()

        response = self.client.get(page.url)
        self.assertEqual(response.status_code, HTTPStatus.OK)

        self.assertContains(response, page.title)
        self.assertContains(response, "Summary")

        # Download UI should not render when the image is missing
        self.assertNotContains(response, "Download this image")
        self.assertNotContains(response, " download")

        # Image block content should render without the image
        self.assertContains(response, "Figure 1")
        self.assertContains(response, "Figure subtitle")
        self.assertContains(response, "Office for National Statistics")
