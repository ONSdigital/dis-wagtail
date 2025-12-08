from datetime import datetime
from unittest.mock import Mock

from django.test import SimpleTestCase, TestCase

from cms.articles.utils import create_data_csv_download_response_from_data, serialize_correction_or_notice


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
