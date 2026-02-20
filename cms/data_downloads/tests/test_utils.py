from unittest.mock import patch

from django.test import SimpleTestCase

from cms.data_downloads.utils import (
    clean_cell_value,
    create_data_csv_download_response_from_data,
    flatten_table_data,
    sanitize_data_for_csv,
)


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
        with patch("cms.data_downloads.utils.BeautifulSoup") as mock_bs:
            clean_cell_value("plain text without html")
            mock_bs.assert_not_called()

            clean_cell_value("text with <b>html</b>")
            mock_bs.assert_called_once()


class SanitizeDataForCsvTests(SimpleTestCase):
    """Tests for the sanitize_data_for_csv function that prevents CSV injection attacks."""

    def test_prepends_quote_to_string_starting_with_equals(self):
        """Test that strings starting with = are prefixed with a single quote."""
        data = [["=SUM(A1:A10)", "normal"]]
        result = sanitize_data_for_csv(data)
        self.assertEqual(result, [["'=SUM(A1:A10)", "normal"]])

    def test_prepends_quote_to_string_starting_with_plus(self):
        """Test that strings starting with + are prefixed with a single quote."""
        data = [["+1234", "normal"]]
        result = sanitize_data_for_csv(data)
        self.assertEqual(result, [["'+1234", "normal"]])

    def test_prepends_quote_to_string_starting_with_minus(self):
        """Test that strings starting with - are prefixed with a single quote."""
        data = [["-cmd|'/c calc'!A1", "normal"]]
        result = sanitize_data_for_csv(data)
        self.assertEqual(result, [["'-cmd|'/c calc'!A1", "normal"]])

    def test_prepends_quote_to_string_starting_with_at(self):
        """Test that strings starting with @ are prefixed with a single quote."""
        data = [["@SUM(1+1)", "normal"]]
        result = sanitize_data_for_csv(data)
        self.assertEqual(result, [["'@SUM(1+1)", "normal"]])

    def test_prepends_quote_to_string_starting_with_tab(self):
        """Test that strings starting with tab character are prefixed with a single quote."""
        data = [["\tvalue", "ONS"]]
        result = sanitize_data_for_csv(data)
        self.assertEqual(result, [["'\tvalue", "ONS"]])

    def test_does_not_modify_normal_strings(self):
        """Test that normal strings without dangerous prefixes are not modified."""
        data = [["Category", "Value 1", "Value 2"]]
        result = sanitize_data_for_csv(data)
        self.assertEqual(result, [["Category", "Value 1", "Value 2"]])

    def test_does_not_modify_numbers(self):
        """Test that numbers which are not strings are not modified."""
        data = [[1, 2, 3]]
        result = sanitize_data_for_csv(data)
        self.assertEqual(result, [[1, 2, 3]])

        data = [[1.5, 2.7, 3.9]]
        result = sanitize_data_for_csv(data)
        self.assertEqual(result, [[1.5, 2.7, 3.9]])

        data = [[-100, -50.5, -999]]
        result = sanitize_data_for_csv(data)
        self.assertEqual(result, [[-100, -50.5, -999]])

    def test_handles_empty_strings(self):
        """Test that empty strings are not modified."""
        data = [["", "value"]]
        result = sanitize_data_for_csv(data)
        self.assertEqual(result, [["", "value"]])

    def test_handles_empty_data(self):
        """Test that empty data list is handled correctly."""
        result = sanitize_data_for_csv([])
        self.assertEqual(result, [])

        data = [[], [], []]
        result = sanitize_data_for_csv(data)
        self.assertEqual(result, [[], [], []])

    def test_handles_mixed_types_in_row(self):
        """Test that rows with mixed data types are handled correctly."""
        data = [["=FORMULA", 123, 45.6, "ONS", "@cmd"]]
        result = sanitize_data_for_csv(data)
        self.assertEqual(result, [["'=FORMULA", 123, 45.6, "ONS", "'@cmd"]])

    def test_handles_multiple_rows(self):
        """Test that multiple rows are all sanitized correctly."""
        data = [
            ["Category", "Value"],
            ["=SUM(A1)", 100],
            ["+cmd", 200],
            ["-formula", 300],
            ["@reference", 400],
        ]
        result = sanitize_data_for_csv(data)
        expected = [
            ["Category", "Value"],
            ["'=SUM(A1)", 100],
            ["'+cmd", 200],
            ["'-formula", 300],
            ["'@reference", 400],
        ]
        self.assertEqual(result, expected)

    def test_only_prepends_quote_if_dangerous_char_is_first(self):
        """Test that dangerous characters in the middle of strings are not modified."""
        data = [["safe+value", "safe=value", "safe-value", "safe@value"]]
        result = sanitize_data_for_csv(data)
        self.assertEqual(result, [["safe+value", "safe=value", "safe-value", "safe@value"]])

    def test_handles_strings_with_whitespace(self):
        """Test that strings with leading dangerous characters are sanitized even with content."""
        data = [["= 1+1", "+ command", "- value", "@ reference"]]
        result = sanitize_data_for_csv(data)
        self.assertEqual(result, [["'= 1+1", "'+ command", "'- value", "'@ reference"]])

    def test_preserves_original_data_structure(self):
        """Test that the original nested list structure is preserved."""
        data = [
            ["Header 1", "Header 2", "Header 3"],
            ["Value 1", "Value 2", "Value 3"],
            ["Value 4", "Value 5", "Value 6"],
        ]
        result = sanitize_data_for_csv(data)
        self.assertEqual(len(result), 3)
        self.assertEqual(len(result[0]), 3)
        self.assertEqual(len(result[1]), 3)
        self.assertEqual(len(result[2]), 3)

    def test_real_world_csv_injection_payloads(self):
        """Test against common CSV injection attack payloads."""
        dangerous_payloads = [
            "=1+2+3",
            "=1+2';!A1",
            "+1+1+cmd|' /C calc'!A1",
            "-1+1+cmd|' /C calc'!A1",
            "@SUM(1+1)*cmd|' /C calc'!A1",
            "=cmd|' /c notepad'!'A1'",
            "\t=cmd",
        ]
        data = [[payload] for payload in dangerous_payloads]
        result = sanitize_data_for_csv(data)

        # All should be prefixed with a single quote
        for row in result:
            self.assertTrue(row[0].startswith("'"))
            self.assertIn(row[0][1], ["=", "+", "-", "@", "\t"])


class CreateDataCsvDownloadResponseFromDataTests(SimpleTestCase):
    def test_returns_csv_content_type(self):
        response = create_data_csv_download_response_from_data([["a", "b"]], title="test")
        self.assertEqual(response["Content-Type"], "text/csv")

    def test_sets_content_disposition_with_slugified_filename(self):
        response = create_data_csv_download_response_from_data([["a", "b"]], title="My Chart")
        self.assertEqual(response["Content-Disposition"], 'attachment; filename="my-chart.csv"')

    def test_slugifies_title_with_special_characters(self):
        response = create_data_csv_download_response_from_data([["a", "b"]], title="Population Growth (2020-2024)!")
        self.assertEqual(response["Content-Disposition"], 'attachment; filename="population-growth-2020-2024.csv"')

    def test_uses_fallback_for_empty_title(self):
        response = create_data_csv_download_response_from_data([["a", "b"]], title="")
        self.assertEqual(response["Content-Disposition"], 'attachment; filename="chart.csv"')

    def test_slugifies_long_complex_title(self):
        title = (
            "Figure 4: Output per worker using RTI data grew by 1.7%, while output per worker using LFS data "
            "grew by 1.4% in January to March 2025, compared with 2019 (average level)"
        )
        expected_filename = (
            "figure-4-output-per-worker-using-rti-data-grew-by-17-while-output-per-worker-using-lfs-data-"
            "grew-by-14-in-january-to-march-2025-compared-with-2019-average-level"
        )
        response = create_data_csv_download_response_from_data([["a", "b"]], title=title)
        self.assertEqual(response["Content-Disposition"], f'attachment; filename="{expected_filename}.csv"')

    def test_writes_data_rows_to_csv(self):
        data = [
            ["Category", "Value 1", "Value 2"],
            ["2020", "100", "150"],
            ["2021", "120", "180"],
        ]
        response = create_data_csv_download_response_from_data(data, title="test")
        content = response.content.decode("utf-8")

        self.assertIn("Category,Value 1,Value 2", content)
        self.assertIn("2020,100,150", content)
        self.assertIn("2021,120,180", content)

    def test_handles_empty_data(self):
        # This is an edge case as all charts will have some data
        response = create_data_csv_download_response_from_data([], title="empty")
        self.assertEqual(response.content.decode("utf-8"), "")
