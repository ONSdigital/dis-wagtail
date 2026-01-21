import urllib.parse
from unittest.mock import Mock, patch

from django.http import HttpRequest, HttpResponsePermanentRedirect, HttpResponseRedirect
from django.test import RequestFactory, SimpleTestCase, TestCase, override_settings

from cms.articles.tests.factories import StatisticalArticlePageFactory
from cms.core.utils import (
    clean_cell_value,
    flatten_table_data,
    get_client_ip,
    get_content_type_for_page,
    latex_formula_to_svg,
    redirect,
    redirect_to_parent_listing,
)
from cms.methodology.tests.factories import MethodologyPageFactory
from cms.topics.tests.factories import TopicPageFactory


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


class LatexFormulaTestCase(TestCase):
    def test_latex_formula_to_svg_simple_formula(self):
        """Test the conversion of LaTeX formula to SVG."""
        # Test with a simple LaTeX formula
        latex_formula = r"\frac{a}{b}"
        result = latex_formula_to_svg(latex_formula)
        self.assertTrue(result.startswith("<svg"))
        self.assertIn("</g>", result)
        self.assertTrue(result.endswith("</svg>\n"))

    def test_latex_formula_to_svg_complex_formula(self):
        """Test the conversion of a more complex LaTeX formula to SVG."""
        # Test with a more complex LaTeX formula
        latex_formula = r"{{(^B \,Oct\,(T - 1)\, + \,^B \,Nov\,(T\, + \,2)\,)} \over 4}\, + \,{{3\,*\,(^B \,Nov\,(T - 1)\, + \,^B \,Oct\,(T\, + \,2)\,)} \over 4}\, + \sum\limits_{i = Dec\,\,(T - 1)}^{i = Sep\,\,(T + 2)} {B_i }"  # noqa: E501 pylint: disable=line-too-long
        result = latex_formula_to_svg(latex_formula)
        self.assertTrue(result.startswith("<svg"))
        self.assertIn("</g>", result)
        self.assertTrue(result.endswith("</svg>\n"))

    def test_latex_formula_to_svg_formula_with_background(self):
        """Test the conversion of a LaTeX formula to SVG with a background."""
        # Test with a LaTeX formula with a background
        latex_formula = r"\frac{a}{b}"
        result = latex_formula_to_svg(latex_formula, transparent=False)
        self.assertTrue(result.startswith("<svg"))
        self.assertIn("fill: #ffffff", result)

        result = latex_formula_to_svg(latex_formula, transparent=True)
        self.assertTrue(result.startswith("<svg"))
        self.assertNotIn("fill: #ffffff", result)

    def test_latex_formula_to_svg_with_advanced_mathematical_symbols(self):
        latex_formula = (
            r"\begin{bmatrix}"
            r"{a_{11}}&{a_{12}}&{\cdots}&{a_{1n}}\\"
            r"{a_{21}}&{a_{22}}&{\cdots}&{a_{2n}}\\"
            r"{\vdots}&{\vdots}&{\ddots}&{\vdots}\\"
            r"{a_{m1}}&{a_{m2}}&{\cdots}&{a_{mn}}\\"
            r"\end{bmatrix}"
        )
        result = latex_formula_to_svg(latex_formula)
        self.assertTrue(result.startswith("<svg"))
        self.assertIn("</g>", result)
        self.assertTrue(result.endswith("</svg>\n"))

    def test_latex_formula_to_svg_empty_formula(self):
        """Test the conversion of an empty LaTeX formula to SVG."""
        # Test with an empty LaTeX formula
        latex_formula = ""
        with self.assertRaises(RuntimeError):
            latex_formula_to_svg(latex_formula)

    def test_latex_formula_to_svg_invalid_formula(self):
        """Test the conversion of an invalid LaTeX formula to SVG."""
        # Test with an invalid LaTeX formula
        latex_formula = r"\frac{a}{b"
        with self.assertRaises(RuntimeError):
            latex_formula_to_svg(latex_formula)


class TestContentTypeForPage(TestCase):
    def test_get_content_type_for_page(self):
        """Test the content type for a given page."""
        # Create a dummy page
        page = StatisticalArticlePageFactory(title="Test Article")
        content_type = get_content_type_for_page(page)
        self.assertEqual(content_type, "Article")

        page = TopicPageFactory(title="Test Topic")
        content_type = get_content_type_for_page(page)
        self.assertEqual(content_type, "Topic")

        page = MethodologyPageFactory(title="Test Methodology")
        content_type = get_content_type_for_page(page)
        self.assertEqual(content_type, "Methodology")


class RedirectToParentListingTestCase(SimpleTestCase):
    def setUp(self):
        self.request = HttpRequest()
        self.parent = Mock(spec_set=["get_url", "get_articles_search_url"])
        self.page = Mock()
        self.page.get_parent.return_value.specific_deferred = self.parent

    def test_redirects_to_root_if_no_parent(self):
        self.page.get_parent.return_value = None
        response = redirect_to_parent_listing(
            page=self.page, request=self.request, listing_url_method_name="get_articles_search_url"
        )
        self.assertIsInstance(response, HttpResponseRedirect)
        self.assertEqual(response.url, "/")

    def test_redirects_to_listing_url_if_method_exists_and_returns_url(self):
        self.parent.get_articles_search_url = Mock(return_value="/articles/search/")
        response = redirect_to_parent_listing(
            page=self.page, request=self.request, listing_url_method_name="get_articles_search_url"
        )
        self.assertIsInstance(response, HttpResponseRedirect)
        self.assertEqual(response.status_code, 307)
        self.assertEqual(response.url, "/articles/search/")

    def test_redirects_to_parent_url_if_listing_method_missing(self):
        self.parent.get_url = Mock(return_value="/parent/")
        response = redirect_to_parent_listing(
            page=self.page, request=self.request, listing_url_method_name="nonexistent_method"
        )
        self.assertIsInstance(response, HttpResponseRedirect)
        self.assertEqual(response.url, "/parent/")

    def test_redirects_to_parent_url_if_listing_method_returns_none(self):
        self.parent.get_articles_search_url = Mock(return_value=None)
        self.parent.get_url = Mock(return_value="/parent/")
        response = redirect_to_parent_listing(
            page=self.page, request=self.request, listing_url_method_name="get_articles_search_url"
        )
        self.assertIsInstance(response, HttpResponseRedirect)
        self.assertEqual(response.url, "/parent/")


class FlattenTableDataTestCase(SimpleTestCase):
    def test_flattens_headers_and_rows(self):
        """Test that headers and rows are correctly flattened."""
        data = {
            "headers": [
                [{"value": "Header 1"}, {"value": "Header 2"}, {"value": "Header 3"}],
            ],
            "rows": [
                [{"value": "Row 1 Col 1"}, {"value": "Row 1 Col 2"}, {"value": "Row 1 Col 3"}],
                [{"value": "Row 2 Col 1"}, {"value": "Row 2 Col 2"}, {"value": "Row 2 Col 3"}],
            ],
        }
        result = flatten_table_data(data)
        expected = [
            ["Header 1", "Header 2", "Header 3"],
            ["Row 1 Col 1", "Row 1 Col 2", "Row 1 Col 3"],
            ["Row 2 Col 1", "Row 2 Col 2", "Row 2 Col 3"],
        ]
        self.assertEqual(result, expected)

    def test_handles_empty_data(self):
        """Test that empty data returns an empty list."""
        data = {}
        result = flatten_table_data(data)
        self.assertEqual(result, [])

    def test_handles_empty_headers_and_rows(self):
        """Test that empty headers and rows return an empty list."""
        data = {"headers": [], "rows": []}
        result = flatten_table_data(data)
        self.assertEqual(result, [])

    def test_handles_missing_values(self):
        """Test that missing values are replaced with empty strings."""
        data = {
            "headers": [
                [{"value": "Header 1"}, {}, {"value": "Header 3"}],
            ],
            "rows": [
                [{}, {"value": "Row 1 Col 2"}, {"value": "Row 1 Col 3"}],
            ],
        }
        result = flatten_table_data(data)
        expected = [
            ["Header 1", "", "Header 3"],
            ["", "Row 1 Col 2", "Row 1 Col 3"],
        ]
        self.assertEqual(result, expected)

    def test_handles_multiple_header_rows(self):
        """Test that multiple header rows are correctly flattened."""
        data = {
            "headers": [
                [{"value": "Header 1"}, {"value": "Header 2"}],
                [{"value": "Subheader 1"}, {"value": "Subheader 2"}],
            ],
            "rows": [
                [{"value": "Row 1 Col 1"}, {"value": "Row 1 Col 2"}],
            ],
        }
        result = flatten_table_data(data)
        expected = [
            ["Header 1", "Header 2"],
            ["Subheader 1", "Subheader 2"],
            ["Row 1 Col 1", "Row 1 Col 2"],
        ]
        self.assertEqual(result, expected)

    def test_colspan_repeats_value(self):
        """Test that colspan cells have their value repeated across columns."""
        data = {
            "headers": [
                [{"value": "Merged Header", "colspan": 2}, {"value": "Header 3"}],
            ],
            "rows": [
                [{"value": "A"}, {"value": "B"}, {"value": "C"}],
            ],
        }
        result = flatten_table_data(data)
        expected = [
            ["Merged Header", "Merged Header", "Header 3"],
            ["A", "B", "C"],
        ]
        self.assertEqual(result, expected)

        # Test with colspan in rows
        data = {
            "headers": [],
            "rows": [
                [{"value": "Merged Cell", "colspan": 2}, {"value": "C1"}],
                [{"value": "A2"}, {"value": "B2"}, {"value": "C2"}],
            ],
        }
        result = flatten_table_data(data)
        expected = [
            ["Merged Cell", "Merged Cell", "C1"],
            ["A2", "B2", "C2"],
        ]
        self.assertEqual(result, expected)

    def test_rowspan_repeats_value(self):
        """Test that rowspan cells have their value repeated across rows."""
        data = {
            "headers": [],
            "rows": [
                [{"value": "Merged", "rowspan": 2}, {"value": "B1"}],
                [{"value": "B2"}],
            ],
        }
        result = flatten_table_data(data)
        expected = [
            ["Merged", "B1"],
            ["Merged", "B2"],
        ]
        self.assertEqual(result, expected)

    def test_colspan_and_rowspan_combined(self):
        """Test that cells with both colspan and rowspan are handled correctly."""
        data = {
            "headers": [],
            "rows": [
                [{"value": "Merged", "colspan": 2, "rowspan": 2}, {"value": "C1"}],
                [{"value": "C2"}],
                [{"value": "A3"}, {"value": "B3"}, {"value": "C3"}],
            ],
        }
        result = flatten_table_data(data)
        expected = [
            ["Merged", "Merged", "C1"],
            ["Merged", "Merged", "C2"],
            ["A3", "B3", "C3"],
        ]
        self.assertEqual(result, expected)

        # Test with headers and cells merged both ways in the middle
        data = {
            "headers": [[{"value": "Header 1"}, {"value": "Header 2"}, {"value": "Header 3"}, {"value": "Header 4"}]],
            "rows": [
                [{"value": "A1"}, {"value": "Merged", "colspan": 2, "rowspan": 2}, {"value": "C1"}],
                [{"value": "A2"}, {"value": "C2"}],
                [{"value": "A3"}, {"value": "B3"}, {"value": "C3"}, {"value": "D3"}],
            ],
        }
        result = flatten_table_data(data)
        expected = [
            ["Header 1", "Header 2", "Header 3", "Header 4"],
            ["A1", "Merged", "Merged", "C1"],
            ["A2", "Merged", "Merged", "C2"],
            ["A3", "B3", "C3", "D3"],
        ]
        self.assertEqual(result, expected)

    def test_rowspan_at_end_of_row(self):
        """Test that rowspan cells at the end of a row are handled correctly."""
        data = {
            "headers": [],
            "rows": [
                [{"value": "A1"}, {"value": "Merged", "rowspan": 2}],
                [{"value": "A2"}],
            ],
        }
        result = flatten_table_data(data)
        expected = [
            ["A1", "Merged"],
            ["A2", "Merged"],
        ]
        self.assertEqual(result, expected)

    def test_multiple_rowspans_in_same_row(self):
        """Test that multiple rowspan cells in the same row are handled correctly."""
        data = {
            "headers": [],
            "rows": [
                [{"value": "A", "rowspan": 2}, {"value": "B"}, {"value": "C", "rowspan": 3}],
                [{"value": "B2"}],
                [{"value": "A3"}, {"value": "B3"}],
            ],
        }
        result = flatten_table_data(data)
        expected = [
            ["A", "B", "C"],
            ["A", "B2", "C"],
            ["A3", "B3", "C"],
        ]
        self.assertEqual(result, expected)

    def test_colspan_with_default_value(self):
        """Test that colspan=1 (default) doesn't duplicate values."""
        data = {
            "headers": [],
            "rows": [
                [{"value": "A", "colspan": 1}, {"value": "B"}],
            ],
        }
        result = flatten_table_data(data)
        expected = [
            ["A", "B"],
        ]
        self.assertEqual(result, expected)

    def test_rowspan_with_default_value(self):
        """Test that rowspan=1 (default) doesn't duplicate values."""
        data = {
            "headers": [],
            "rows": [
                [{"value": "A", "rowspan": 1}],
                [{"value": "B"}],
            ],
        }
        result = flatten_table_data(data)
        expected = [
            ["A"],
            ["B"],
        ]
        self.assertEqual(result, expected)

    def test_numeric_values_preserved(self):
        """Test that numeric values (int and float) are preserved."""
        data = {
            "headers": [[{"value": "Name"}, {"value": "Count"}, {"value": "Rate"}]],
            "rows": [
                [{"value": "Item A"}, {"value": 42}, {"value": 3.14}],
                [{"value": "Item B"}, {"value": 0}, {"value": -2.5}],
            ],
        }
        result = flatten_table_data(data)
        expected = [
            ["Name", "Count", "Rate"],
            ["Item A", 42, 3.14],
            ["Item B", 0, -2.5],
        ]
        self.assertEqual(result, expected)

    def test_html_stripped_from_values_except_links(self):
        """Test that HTML tags are stripped except anchor tags."""
        data = {
            "headers": [[{"value": "<b>Header</b>"}]],
            "rows": [
                [{"value": "<p>Paragraph</p>"}],
                [{"value": '<a href="#">Link</a>'}],
            ],
        }
        result = flatten_table_data(data)
        expected = [
            ["Header"],
            ["Paragraph"],
            ['<a href="#">Link</a>'],
        ]
        self.assertEqual(result, expected)

    def test_br_tags_converted_to_newlines(self):
        """Test that <br> tags are converted to newlines."""
        data = {
            "headers": [],
            "rows": [
                [{"value": "Line 1<br/>Line 2"}],
                [{"value": "A<br>B<br/>C"}],
            ],
        }
        result = flatten_table_data(data)
        expected = [
            ["Line 1\nLine 2"],
            ["A\nB\nC"],
        ]
        self.assertEqual(result, expected)

    def test_whitespace_stripped(self):
        """Test that leading and trailing whitespace is stripped from values."""
        data = {
            "headers": [[{"value": "  Header  "}]],
            "rows": [[{"value": "\t Value \n"}]],
        }
        result = flatten_table_data(data)
        expected = [
            ["Header"],
            ["Value"],
        ]
        self.assertEqual(result, expected)


class RedirectUtilityTestCase(SimpleTestCase):
    def test_temporary_redirect_default(self):
        response = redirect("/foo")
        self.assertIsInstance(response, HttpResponseRedirect)
        self.assertEqual(response.status_code, 307)
        self.assertEqual(response.url, "/foo")

    def test_temporary_redirect_preserve_request_false(self):
        response = redirect("/bar", preserve_request=False)
        self.assertIsInstance(response, HttpResponseRedirect)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/bar")

    def test_permanent_redirect_preserve_request_false(self):
        response = redirect("/baz", permanent=True, preserve_request=False)
        self.assertIsInstance(response, HttpResponsePermanentRedirect)
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response.url, "/baz")

    def test_permanent_redirect_preserve_request_true(self):
        response = redirect("/qux", permanent=True, preserve_request=True)
        self.assertIsInstance(response, HttpResponsePermanentRedirect)
        self.assertEqual(response.status_code, 308)
        self.assertEqual(response.url, "/qux")

    def test_temporary_redirect_preserve_request_true(self):
        response = redirect("/quux", preserve_request=True)
        self.assertIsInstance(response, HttpResponseRedirect)
        self.assertEqual(response.status_code, 307)
        self.assertEqual(response.url, "/quux")

    def test_args_are_passed(self):
        # HttpResponseRedirect only uses the first positional argument (the URL)
        response = redirect("/args-test", "unused-arg")
        self.assertEqual(response.url, "/args-test")

    def test_unicode_url(self):
        response = redirect("/unicodé")
        expected_url = urllib.parse.quote("/unicodé", safe="/:")
        self.assertEqual(response.url, expected_url)


class CleanCellValueTestCase(SimpleTestCase):
    def test_returns_numerical_values_unchanged(self):
        """Test that numerical values are returned unchanged."""
        self.assertEqual(clean_cell_value(42), 42)
        self.assertEqual(clean_cell_value(0), 0)
        self.assertEqual(clean_cell_value(-10), -10)
        self.assertEqual(clean_cell_value(3.14), 3.14)
        self.assertEqual(clean_cell_value(0.0), 0.0)
        self.assertEqual(clean_cell_value(-2.5), -2.5)

    def test_strips_whitespace(self):
        """Test that leading and trailing whitespace is stripped."""
        self.assertEqual(clean_cell_value("  hello  "), "hello")
        self.assertEqual(clean_cell_value("\t\ntext\n\t"), "text")

    def test_converts_br_tags_to_newlines(self):
        """Test that <br> tag variations are converted to newlines."""
        self.assertEqual(clean_cell_value("line1<br/>line2"), "line1\nline2")
        self.assertEqual(clean_cell_value("line1<br>line2"), "line1\nline2")
        self.assertEqual(clean_cell_value("a<br/>b<br>c"), "a\nb\nc")
        # Test case insensitivity and spacing variations
        self.assertEqual(clean_cell_value("a<BR>b"), "a\nb")
        self.assertEqual(clean_cell_value("a<Br/>b"), "a\nb")
        self.assertEqual(clean_cell_value("a<br />b"), "a\nb")

    def test_strips_html_tags_except_anchors(self):
        """Test that HTML tags are stripped except anchor tags."""
        self.assertEqual(clean_cell_value("<b>bold</b>"), "bold")
        self.assertEqual(clean_cell_value("<p>paragraph</p>"), "paragraph")
        self.assertEqual(clean_cell_value("<span class='foo'>span</span>"), "span")
        self.assertEqual(clean_cell_value("<div>div</div>"), "div")
        self.assertEqual(clean_cell_value("<em>emphasis</em>"), "emphasis")
        self.assertEqual(clean_cell_value("<strong>strong</strong>"), "strong")

    def test_combined_html_and_br_handling(self):
        """Test that HTML stripping and BR conversion work together."""
        self.assertEqual(clean_cell_value("<b>bold</b><br/><i>italic</i>"), "bold\nitalic")
        self.assertEqual(clean_cell_value("  <p>text<br>more</p>  "), "text\nmore")

    def test_preserves_anchor_tags(self):
        """Test that anchor tags are preserved while other tags are stripped."""
        # Note: BeautifulSoup normalizes quotes to double quotes
        self.assertEqual(clean_cell_value("<a href='#'>link</a>"), '<a href="#">link</a>')
        self.assertEqual(
            clean_cell_value('<a href="https://example.com">Example</a>'),
            '<a href="https://example.com">Example</a>',
        )
        self.assertEqual(
            clean_cell_value('<a href="/path" class="link">styled link</a>'),
            '<a class="link" href="/path">styled link</a>',
        )

    def test_preserves_anchor_tags_mixed_with_other_html(self):
        """Test that anchors are preserved while other HTML is stripped."""
        self.assertEqual(
            clean_cell_value("<b>Bold</b> and <a href='#'>link</a>"),
            'Bold and <a href="#">link</a>',
        )
        self.assertEqual(
            clean_cell_value("<p><a href='#'>link</a> in paragraph</p>"),
            '<a href="#">link</a> in paragraph',
        )
        self.assertEqual(
            clean_cell_value("<a href='#'>link1</a><br/><a href='#'>link2</a>"),
            '<a href="#">link1</a>\n<a href="#">link2</a>',
        )

    def test_preserves_anchor_tags_case_insensitive(self):
        """Test that anchor tags are preserved regardless of case."""
        # Note: BeautifulSoup normalizes tag names to lowercase and quotes to double quotes
        self.assertEqual(clean_cell_value("<A href='#'>LINK</A>"), '<a href="#">LINK</a>')
        self.assertEqual(clean_cell_value("<A HREF='#'>link</A>"), '<a href="#">link</a>')

    def test_strips_tags_starting_with_a(self):
        """Test that HTML tags starting with 'a' (but not anchor tags) are stripped."""
        self.assertEqual(clean_cell_value("<abbr>abbreviation</abbr>"), "abbreviation")
        self.assertEqual(clean_cell_value("<article>content</article>"), "content")
        self.assertEqual(clean_cell_value("<aside>sidebar</aside>"), "sidebar")
        self.assertEqual(clean_cell_value("<address>addr</address>"), "addr")

    def test_self_closing_anchor_preserved(self):
        """Test that self-closing anchor syntax is preserved (normalized by BeautifulSoup)."""
        self.assertEqual(clean_cell_value("<a href='#'/>"), '<a href="#"></a>')

    def test_preserves_less_than_symbols_in_content(self):
        """Test that < symbols in content are preserved for CSV output."""
        self.assertEqual(clean_cell_value("<b>a <- b</b>"), "a <- b")
        self.assertEqual(clean_cell_value("<p>5 < 10</p>"), "5 < 10")
        self.assertEqual(clean_cell_value("a < b"), "a < b")

    def test_empty_string(self):
        """Test that empty strings are handled correctly."""
        self.assertEqual(clean_cell_value(""), "")
        self.assertEqual(clean_cell_value("   "), "")

    def test_plain_string(self):
        """Test that plain strings without HTML are returned stripped."""
        self.assertEqual(clean_cell_value("plain text"), "plain text")

    def test_skips_beautifulsoup_for_plain_strings(self):
        """Test that BeautifulSoup is not instantiated for strings without '<'."""
        with patch("cms.core.utils.BeautifulSoup") as mock_bs:
            clean_cell_value("plain text without html")
            mock_bs.assert_not_called()

            clean_cell_value("text with <b>html</b>")
            mock_bs.assert_called_once()
