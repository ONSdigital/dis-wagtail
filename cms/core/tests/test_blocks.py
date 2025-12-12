# pylint: disable=too-many-lines
from datetime import datetime
from unittest.mock import Mock
from urllib.parse import urlparse

from django.test import TestCase
from wagtail.blocks import StreamBlockValidationError, StructBlockValidationError
from wagtail.rich_text import RichText
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
from cms.core.blocks.glossary_terms import GlossaryTermsBlock
from cms.core.tests.factories import GlossaryTermFactory
from cms.core.tests.utils import get_test_document
from cms.home.models import HomePage


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
        self.assertIsNone(value.link)

        value = block.to_python(
            {
                "external_url": "https://ons.gov.uk",
                "title": "Example",
                "description": "A link",
                "content_type": "ARTICLE",
            }
        )

        self.assertDictEqual(
            value.link,
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
            value.link,
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
            value.link,
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
            value.link,
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


class GlossaryTermBlockTestCase(TestCase):
    """Test for Glossary Term block."""

    def test_glossary_term_block_clean_method_removes_duplicates(self):
        """Test that the clean method of the GlossaryTermsBlock removes duplicated instances of glossary terms."""
        term = GlossaryTermFactory()
        another_term = GlossaryTermFactory()
        block = GlossaryTermsBlock()

        value = block.to_python([term.pk, term.pk, another_term.pk])
        clean_value = block.clean(value)

        self.assertEqual(len(clean_value), 2)
        self.assertEqual(clean_value[0].pk, term.pk)
        self.assertEqual(clean_value[1].pk, another_term.pk)

    def test_glossary_term_block__get_context(self):
        """Test that get_context returns correctly formatted data to be used by the ONS Accordion component."""
        term = GlossaryTermFactory()
        block = GlossaryTermsBlock()

        value = block.to_python([term.pk])
        context = block.get_context(value)

        self.assertListEqual(
            context["formatted_glossary_terms"],
            [
                {
                    "headingLevel": 3,
                    "title": term.name,
                    "content": f'<div class="rich-text">{term.definition}</div>',
                }
            ],
        )


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
                "headers": [[{"value": "header cell", "type": "th"}]],
                "trs": [{"tds": [{"value": "row cell", "type": "td"}]}],
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
        self.assertIn("<table ", rendered)
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

        self.assertTagInHTML(
            '<th scope="col" class="ons-table__header ons-u-ta-center" width="20px">'
            '<span class="ons-table__header-text">header cell</span></th>',
            rendered,
        )
        self.assertTagInHTML('<td class="ons-table__cell ons-u-ta-right">row cell</td>', rendered)
        self.assertIn("header cell", rendered)
        self.assertIn("row cell", rendered)

    def test_render_block__ds_component_markup(self):
        table = {
            "headers": [],
            "rows": [[{"value": "row cell", "type": "td"}]],
        }
        rendered = self.block.render({"data": table})

        expected = """
        <table class="ons-table">
            <tbody class="ons-table__body">
                <tr class="ons-table__row">
                    <td class="ons-table__cell">row cell</td>
                </tr>
            </tbody>
        </table>
        """
        self.assertInHTML(expected, rendered)

        table = {
            "headers": [[{"value": "header cell", "type": "th"}]],
            "rows": [],
        }
        rendered = self.block.render({"data": table})

        expected = """
        <table class="ons-table">
            <thead class="ons-table__head">
                <tr class="ons-table__row">
                    <th scope="col" class="ons-table__header">
                        <span class="ons-table__header-text">header cell</span>
                    </th>
                </tr>
            </thead>
            <tbody class="ons-table__body"></tbody>
        </table>
        """
        self.assertInHTML(expected, rendered)

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

        expected = """
        <table class="ons-table">
            <thead class="ons-table__head">
                <tr class="ons-table__row">
                    <th scope="col" class="ons-table__header" colspan="2">
                        <span class="ons-table__header-text">Combined header</span>
                    </th>
                    <th scope="col" class="ons-table__header">
                        <span class="ons-table__header-text">Regular header</span>
                    </th>
                    <th scope="col" class="ons-table__header" rowspan="2">
                        <span class="ons-table__header-text">Two row header</span>
                    </th>
                </tr>
                <tr class="ons-table__row">
                    <th scope="col" class="ons-table__header">
                        <span class="ons-table__header-text">Sub-header 1</span>
                    </th>
                    <th scope="col" class="ons-table__header">
                        <span class="ons-table__header-text">Sub-header 2</span>
                    </th>
                    <th scope="col" class="ons-table__header">
                        <span class="ons-table__header-text">Sub-header 3</span>
                    </th>
                </tr>
            </thead>
            <tbody class="ons-table__body">
                <tr class="ons-table__row">
                    <th class="ons-table__cell" scope="row">Col header 1</th>
                    <td class="ons-table__cell" colspan="2" rowspan="2">Two rows and cols cell</td>
                    <td class="ons-table__cell">Col cell 1</td>
                </tr>
                <tr class="ons-table__row">
                    <th class="ons-table__cell" scope="row">Col header 2</th>
                    <td class="ons-table__cell" rowspan="2">Col cell 2</td>
                </tr>
                <tr class="ons-table__row">
                    <th class="ons-table__cell" scope="row">Col header 3</th>
                    <td class="ons-table__cell" colspan="3">Col cell 3</td>
                </tr>
            </tbody>
        </table>
        """
        self.assertInHTML(expected, rendered)

    def test__align_to_ons_classname(self):
        scenarios = {"right": "ons-u-ta-right", "left": "ons-u-ta-left", "center": "ons-u-ta-center", "foo": ""}
        for alignment, classname in scenarios.items():
            self.assertEqual(
                self.block._align_to_ons_classname(alignment),  # pylint: disable=protected-access
                classname,
            )

    def test__prepare_cells(self):
        scenarios = [
            (
                [{"value": "header cell", "type": "th", "width": "20px", "align": "center"}],
                [{"value": "header cell", "type": "th", "width": "20px", "thClasses": "ons-u-ta-center"}],
            ),
            (
                [{"value": "row cell", "type": "td", "width": "50%", "align": "right"}],
                [{"value": "row cell", "type": "td", "width": "50%", "tdClasses": "ons-u-ta-right"}],
            ),
        ]
        for cells, expected in scenarios:
            self.assertListEqual(self.block._prepare_cells(cells), expected)  # pylint: disable=protected-access

    def test_ons_table_block_includes_download_config_with_context(self):
        """Test that download_config is added to context when block_id and page are present."""
        page = StatisticalArticlePageFactory()
        context = {
            "block_id": "test-block-id",
            "page": page,
            "request": None,
        }

        result = self.block.get_context(self.full_data, parent_context=context)

        self.assertIn("download_config", result)
        self.assertIn("title", result["download_config"])
        self.assertIn("itemsList", result["download_config"])
        self.assertEqual(result["download_config"]["title"], "Download: The table")
        self.assertEqual(len(result["download_config"]["itemsList"]), 1)
        self.assertIn("CSV", result["download_config"]["itemsList"][0]["text"])
        self.assertIn("url", result["download_config"]["itemsList"][0])

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

        download_url = result["download_config"]["itemsList"][0]["url"]
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

        download_url = result["download_config"]["itemsList"][0]["url"]
        self.assertEqual(download_url, "/economy/articles/test-article/download-table/test-block-id")

    def test_ons_table_block_download_config_missing_without_page(self):
        """Test that download_config is empty when page is missing from context."""
        context = {
            "block_id": "test-block-id",
            "page": None,
            "request": None,
        }

        result = self.block.get_context(self.full_data, parent_context=context)

        # download_config will be added but should be empty dict
        self.assertEqual(result.get("download_config"), {})


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
