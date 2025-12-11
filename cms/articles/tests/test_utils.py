from datetime import datetime
from unittest.mock import Mock

from django.test import SimpleTestCase, TestCase

from cms.articles.utils import (
    create_data_csv_download_response_from_data,
    sanitize_data_for_csv,
    serialize_correction_or_notice,
)


class SerializeCorrectionOrNoticeTests(TestCase):
    def test_serialize_correction_or_notice(self):
        mock_stream_child = Mock()
        mock_stream_child.value = {
            "when": datetime(2023, 10, 26, 10, 30, 0),
            "text": "This is a test correction description.",
        }
        result = serialize_correction_or_notice(mock_stream_child, superseded_url="https://example.com/")

        expected = {
            "text": "Correction",
            "date": {"iso": "2023-10-26T10:30:00", "short": "26 October 2023 10:30am"},
            "description": "This is a test correction description.",
            "url": "https://example.com/",
            "urlText": "View superseded version",
        }
        self.assertDictEqual(result, expected)

        mock_stream_child.value["text"] = "This is a test notice description."

        result = serialize_correction_or_notice(mock_stream_child)

        expected = {
            "text": "Notice",
            "date": {"iso": "2023-10-26T10:30:00", "short": "26 October 2023"},
            "description": "This is a test notice description.",
        }

        self.assertDictEqual(result, expected)


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
