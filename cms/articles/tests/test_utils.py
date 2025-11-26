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
        response = create_data_csv_download_response_from_data([["a", "b"]], filename="test")
        self.assertEqual(response["Content-Type"], "text/csv")

    def test_sets_content_disposition_with_filename(self):
        response = create_data_csv_download_response_from_data([["a", "b"]], filename="my_chart")
        self.assertEqual(response["Content-Disposition"], 'attachment; filename="my_chart.csv"')

    def test_writes_data_rows_to_csv(self):
        data = [
            ["Category", "Value 1", "Value 2"],
            ["2020", "100", "150"],
            ["2021", "120", "180"],
        ]
        response = create_data_csv_download_response_from_data(data, filename="test")
        content = response.content.decode("utf-8")

        self.assertIn("Category,Value 1,Value 2", content)
        self.assertIn("2020,100,150", content)
        self.assertIn("2021,120,180", content)

    def test_handles_empty_data(self):
        # This is an edge case as all charts will have some data
        response = create_data_csv_download_response_from_data([], filename="empty")
        self.assertEqual(response.content.decode("utf-8"), "")
