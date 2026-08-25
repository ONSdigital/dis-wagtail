import os
from http import HTTPStatus
from io import StringIO
from unittest.mock import patch

import responses
from django.conf import settings
from django.core.management import call_command
from django.test import TestCase

from cms.datasets.tests.factories import DatasetFactory
from cms.taxonomy.tests.factories import TopicFactory


def build_detail_response(*, namespace: str, topics: list[str] | None, next_topics: list[str] | None = None) -> dict:
    """Build a dataset detail response, which is in the current/next format."""
    current = {
        "id": namespace,
        "title": f"{namespace} title",
        "description": f"{namespace} description",
        "state": "published",
        "links": {"latest_version": {"href": f"/datasets/{namespace}/editions/2023/versions/1", "id": "1"}},
    }
    if topics is not None:
        current["topics"] = topics

    next_version = {
        "id": namespace,
        "title": f"{namespace} title (unpublished)",
        "description": f"{namespace} description (unpublished)",
        "state": "associated",
        "links": {"latest_version": {"href": f"/datasets/{namespace}/editions/2023/versions/2", "id": "2"}},
    }
    if next_topics is not None:
        next_version["topics"] = next_topics

    return {"current": current, "next": next_version}


def add_detail_response(namespace: str, **kwargs):
    responses.add(
        responses.GET,
        f"{settings.DATASETS_API_BASE_URL}/{namespace}",
        json=build_detail_response(namespace=namespace, **kwargs),
    )


class BackfillDatasetTopicsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.topic = TopicFactory(id="7779", slug="inflationandpriceindices")

    def call_command(self, *args: str) -> str:
        stdout = StringIO()
        call_command("backfill_dataset_topics", *args, stdout=stdout, stderr=StringIO())
        return stdout.getvalue()

    @responses.activate
    def test_backfills_topic_from_the_api(self):
        dataset = DatasetFactory(namespace="cpih01", edition="time-series", version=1)
        add_detail_response("cpih01", topics=["7779"])

        self.call_command()

        dataset.refresh_from_db()
        self.assertEqual(dataset.topic_id, "7779")
        self.assertEqual(dataset.url_path, "/inflationandpriceindices/datasets/cpih01")

    @responses.activate
    def test_backfills_all_editions_and_versions_with_a_single_api_call(self):
        datasets = [
            DatasetFactory(namespace="cpih01", edition="time-series", version=1),
            DatasetFactory(namespace="cpih01", edition="time-series", version=2),
            DatasetFactory(namespace="cpih01", edition="monthly", version=1),
        ]
        add_detail_response("cpih01", topics=["7779"])

        self.call_command()

        for dataset in datasets:
            dataset.refresh_from_db()
            self.assertEqual(dataset.topic_id, "7779")
        self.assertEqual(len(responses.calls), 1)

    @responses.activate
    def test_uses_the_first_topic_as_the_primary(self):
        TopicFactory(id="1234", slug="economy")
        dataset = DatasetFactory(namespace="cpih01", edition="time-series", version=1)
        add_detail_response("cpih01", topics=["7779", "1234"])

        self.call_command()

        dataset.refresh_from_db()
        self.assertEqual(dataset.topic_id, "7779")

    @responses.activate
    def test_falls_back_to_the_unpublished_version_topics(self):
        dataset = DatasetFactory(namespace="cpih01", edition="time-series", version=1)
        responses.add(
            responses.GET,
            f"{settings.DATASETS_API_BASE_URL}/cpih01",
            json={
                "next": {
                    "id": "cpih01",
                    "title": "cpih01 title (unpublished)",
                    "description": "cpih01 description (unpublished)",
                    "state": "associated",
                    "links": {"latest_version": {"href": "/datasets/cpih01/editions/2024/versions/1", "id": "1"}},
                    "topics": ["7779"],
                }
            },
        )

        self.call_command()

        dataset.refresh_from_db()
        self.assertEqual(dataset.topic_id, "7779")

    @responses.activate
    def test_skips_datasets_the_api_has_no_topic_for(self):
        dataset = DatasetFactory(namespace="cpih01", edition="time-series", version=1)
        add_detail_response("cpih01", topics=None)

        self.call_command()

        dataset.refresh_from_db()
        self.assertIsNone(dataset.topic_id)

    @responses.activate
    def test_skips_topics_missing_from_local_taxonomy(self):
        dataset = DatasetFactory(namespace="cpih01", edition="time-series", version=1)
        add_detail_response("cpih01", topics=["9999"])

        self.call_command()

        dataset.refresh_from_db()
        self.assertIsNone(dataset.topic_id)

    @responses.activate
    def test_api_failure_does_not_stop_the_backfill(self):
        failing = DatasetFactory(namespace="failing", edition="time-series", version=1)
        succeeding = DatasetFactory(namespace="cpih01", edition="time-series", version=1)

        responses.add(
            responses.GET, f"{settings.DATASETS_API_BASE_URL}/failing", status=HTTPStatus.INTERNAL_SERVER_ERROR
        )
        add_detail_response("cpih01", topics=["7779"])

        with self.assertLogs("cms.datasets.management.commands.backfill_dataset_topics", level="ERROR"):
            self.call_command()

        failing.refresh_from_db()
        succeeding.refresh_from_db()
        self.assertIsNone(failing.topic_id)
        self.assertEqual(succeeding.topic_id, "7779")

    @responses.activate
    def test_malformed_api_response_does_not_stop_the_backfill(self):
        dataset_error = DatasetFactory(namespace="cpih01", edition="time-series", version=1)
        dataset = DatasetFactory(namespace="cpih02", edition="time-series", version=1)
        responses.add(
            responses.GET,
            f"{settings.DATASETS_API_BASE_URL}/cpih01",
            body="not json",
            content_type="text/plain",
        )
        add_detail_response("cpih02", topics=["7779"])

        with self.assertLogs("cms.datasets.management.commands.backfill_dataset_topics", level="ERROR"):
            self.call_command()

        dataset.refresh_from_db()
        dataset_error.refresh_from_db()

        self.assertIsNone(dataset_error.topic_id)
        self.assertEqual(dataset.topic_id, "7779")

    @responses.activate
    def test_dry_run_does_not_update_database(self):
        dataset = DatasetFactory(namespace="cpih01", edition="time-series", version=1)
        add_detail_response("cpih01", topics=["7779"])

        self.call_command("--dry-run")

        dataset.refresh_from_db()
        self.assertIsNone(dataset.topic_id)

    @responses.activate
    def test_leaves_datasets_that_already_have_a_topic_alone(self):
        other_topic = TopicFactory(id="1234", slug="economy")
        dataset = DatasetFactory(namespace="cpih01", edition="time-series", version=1, topic=other_topic)

        self.call_command()

        dataset.refresh_from_db()
        self.assertEqual(dataset.topic_id, "1234")
        self.assertEqual(len(responses.calls), 0)

    @responses.activate
    def test_access_token_is_sent_to_api(self):
        DatasetFactory(namespace="cpih01", edition="time-series", version=1)
        responses.add(
            responses.GET,
            f"{settings.DATASETS_API_BASE_URL}/cpih01",
            json=build_detail_response(namespace="cpih01", topics=["7779"]),
            match=[responses.matchers.header_matcher({"Authorization": "Bearer test-token"})],
        )

        self.call_command("--access-token", "Bearer test-token")

        self.assertEqual(len(responses.calls), 1)

    @responses.activate
    def test_access_token_falls_back_to_the_environment(self):
        DatasetFactory(namespace="cpih01", edition="time-series", version=1)
        responses.add(
            responses.GET,
            f"{settings.DATASETS_API_BASE_URL}/cpih01",
            json=build_detail_response(namespace="cpih01", topics=["7779"]),
            match=[responses.matchers.header_matcher({"Authorization": "Bearer env-token"})],
        )

        with patch.dict(os.environ, {"DATASETS_API_ACCESS_TOKEN": "Bearer env-token"}):
            self.call_command()

        self.assertEqual(len(responses.calls), 1)
