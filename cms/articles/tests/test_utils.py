from datetime import datetime
from unittest.mock import Mock

from django.test import TestCase

from cms.articles.utils import serialize_correction_or_notice


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
