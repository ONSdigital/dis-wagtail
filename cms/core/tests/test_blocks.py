from django.conf import settings
from django.test import TestCase
from wagtail.blocks import StreamBlockValidationError, StructBlockValidationError
from wagtail.rich_text import RichText

from cms.core.blocks import (
    BasicTableBlock,
    DocumentBlock,
    DocumentsBlock,
    HeadingBlock,
    ONSEmbedBlock,
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
                "thumbnail": True,
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
                    "thumbnail": True,
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
            [{"url": "#the-heading", "text": "The Heading"}],
        )

    def test_onsemebedblock__clean(self):
        """Check the ONSEmbedBlock validates the supplied URL."""
        block = ONSEmbedBlock()

        with self.assertRaises(StructBlockValidationError) as info:
            value = block.to_python({"url": "https://ons.gov.uk"})
            block.clean(value)

        self.assertEqual(
            info.exception.block_errors["url"].message, f"The URL must start with {settings.ONS_EMBED_PREFIX}"
        )

    def test_onsemebedblock__clean__happy_path(self):
        """Check the ONSEmbedBlock clean method returns the value."""
        block = ONSEmbedBlock()
        value = block.to_python({"url": settings.ONS_EMBED_PREFIX})
        self.assertEqual(block.clean(value), value)

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

    def test_relatedcontentblock_clean__happy_path(self):
        """Happy path for the RelatedContentBlock validation."""
        block = RelatedContentBlock()
        value = block.to_python({"external_url": "https://ons.gov.uk", "title": "The link", "description": ""})

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
            }
        )

        self.assertDictEqual(
            value.link,
            {
                "url": "https://ons.gov.uk",
                "text": "Example",
                "description": "A link",
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
            },
        )

    def test_relatedlinksblock__get_context(self):
        """Check that RelatedLinksBlock heading and slug are in the context."""
        block = RelatedLinksBlock()
        value = block.to_python([])

        context = block.get_context(value)
        self.assertEqual(context["heading"], "Related links")
        self.assertEqual(context["slug"], "related-links")

    def test_relatedlinksblock__toc(self):
        """Check the RelatedLinksBlock TOC."""
        block = RelatedLinksBlock()
        self.assertEqual(
            block.to_table_of_contents_items(block.to_python([])), [{"url": "#related-links", "text": "Related links"}]
        )

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

    def test_documents_block__get_context(self):
        """Test that get_context returns correctly formatted data to be used by the ONS Accordion component."""
        term = GlossaryTermFactory()
        block = GlossaryTermsBlock()

        value = block.to_python([term.pk])
        context = block.get_context(value)

        self.assertListEqual(
            context["formatted_glossary_terms"],
            [
                {
                    "title": term.name,
                    "content": term.definition,
                }
            ],
        )


class ONSTableBlockTestCase(TestCase):
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
