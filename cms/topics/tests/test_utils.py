from django.test import TestCase
from wagtail.blocks import StreamValue

from cms.taxonomy.tests.factories import TopicFactory
from cms.topics.blocks import TimeSeriesPageStoryBlock
from cms.topics.utils import format_time_series_as_document_list, get_topic_search_url


class TestUtils(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.suffix = "search"
        cls.topic = TopicFactory(slug="my-topic")

    def test_format_time_series_as_document_list(self):
        title = "Test Time Series"
        url = "https://example.com/dataset"
        description = "This is a Time Series page summary."

        block_value = {"title": title, "url": url, "description": description}

        time_series_data = StreamValue(
            TimeSeriesPageStoryBlock(),
            stream_data=[
                ("time_series_page_link", block_value),
            ],
        )

        formatted_time_series = format_time_series_as_document_list(time_series_data)

        expected = {
            "title": {"text": title, "url": url},
            "metadata": {"object": {"text": "Time series"}},
            "description": f"<p>{description}</p>",
        }

        self.assertEqual(len(formatted_time_series), 1)
        self.assertEqual(formatted_time_series[0], expected)

    def test_get_topic_search_url_returns_correct_url(self):
        result = get_topic_search_url(self.topic, self.suffix)
        self.assertEqual(result, "/my-topic/search")
