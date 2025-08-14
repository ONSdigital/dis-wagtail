import responses
from django.conf import settings
from django.test import TestCase

from cms.datasets.models import ONSDataset, ONSDatasetApiQuerySet


class TestONSDatasetApiQuerySet(TestCase):
    @responses.activate
    def test_count_uses_total_count(self):
        responses.add(responses.GET, settings.DATASETS_BASE_API_URL, json={"total_count": 2, "count": 0, "items": []})
        api_queryset = ONSDatasetApiQuerySet()
        api_queryset.base_url = settings.DATASETS_BASE_API_URL
        api_queryset.pagination_style = "offset-limit"
        self.assertEqual(api_queryset.count(), 2)

    @responses.activate
    def test_count_defaults_to_item_count(self):
        responses.add(
            responses.GET,
            settings.DATASETS_BASE_API_URL,
            json={
                "items": [
                    {"dummy": "test"},
                    {"dummy": "test2"},
                ]
            },
        )

        api_queryset = ONSDatasetApiQuerySet()
        api_queryset.base_url = settings.DATASETS_BASE_API_URL
        self.assertEqual(api_queryset.count(), 2)


class TestONSDataset(TestCase):
    @responses.activate
    def test_object_from_query_data(self):
        response_dataset = {
            "id": "test1",
            "description": "test 1 description",
            "title": "test 1 title",
            "version": 1,
            "links": {
                "latest_version": {
                    "href": "/datasets/test1/editions/test1_edition/versions/1",
                    "id": "test1",
                },
            },
        }
        responses.add(
            responses.GET,
            settings.DATASETS_BASE_API_URL,
            json={
                "items": [
                    response_dataset,
                ]
            },
        )

        dataset = ONSDataset.objects.all().first()  # pylint: disable=no-member
        self.assertEqual(dataset.title, response_dataset["title"])
        self.assertEqual(dataset.id, response_dataset["id"])
        self.assertEqual(dataset.description, response_dataset["description"])
        self.assertEqual(dataset.edition, "test1_edition")
