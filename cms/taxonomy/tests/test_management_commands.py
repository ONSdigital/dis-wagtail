from collections.abc import Iterable
from typing import Any
from unittest.mock import Mock, patch

import requests
from django.core.management import call_command
from django.test import TestCase
from requests import HTTPError

from cms.taxonomy.management.commands import sync_topics
from cms.taxonomy.models import Topic
from cms.taxonomy.tests.factories import TopicFactory


class SyncTopicsTests(TestCase):
    def setUp(self):
        self.requests_patcher = patch("cms.taxonomy.management.commands.sync_topics.requests")
        self.mock_requests = self.requests_patcher.start()

    def tearDown(self):
        self.mock_requests.stop()

    def test_sync_no_topics(self):
        # Given
        mock_response = mock_successful_json_response([])
        self.mock_requests.get.return_value = mock_response

        # When
        call_command("sync_topics")

        # Then
        self.mock_requests.get.assert_called_once()
        self.assertEqual(Topic.objects.all().count(), 0, "Expect no topics to be saved")

    def test_sync_empty_response(self):
        # Given
        mock_response = Mock(spec=requests.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {}
        self.mock_requests.get.return_value = mock_response

        # When
        call_command("sync_topics")

        # Then
        self.mock_requests.get.assert_called_once()
        self.assertEqual(Topic.objects.all().count(), 0, "Expect no topics to be saved")

    def template_test_sync_one_valid_topic(self, topic: Topic) -> None:
        # Given
        mock_response = mock_successful_json_response([build_topic_api_json(topic)])
        self.mock_requests.get.return_value = mock_response

        # When
        call_command("sync_topics")

        # Then
        self.mock_requests.get.assert_called_once()
        self.assertEqual(Topic.objects.all().count(), 1, "Expect one topic to be saved")
        saved_topic = Topic.objects.first()
        self.assertEqual(saved_topic, topic, "Expect the saved topic to match")

    def test_sync_valid_topic(self):
        topic = create_topic("1234")
        self.template_test_sync_one_valid_topic(topic)

    def test_sync_valid_topic_no_description(self):
        topic = create_topic("1234", include_description=False)
        self.template_test_sync_one_valid_topic(topic)

    def test_sync_valid_topic_no_slug(self):
        """Check that when we attempt to sync a Topic without a slug from the API,
        then an IntegrityError is raised and a warning is logged.
        """
        topic = create_topic(topic_id="123", include_slug=False)

        with self.assertLogs("cms.taxonomy", level="WARNING") as logs:  # , self.assertRaises(IntegrityError):
            # Given
            mock_response = mock_successful_json_response([build_topic_api_json(topic)])
            self.mock_requests.get.return_value = mock_response

            # When
            call_command("sync_topics")

            self.assertEqual(logs.records[0].message, "Cannot create topic: missing slug.")
            self.assertEqual(logs.records[0].topic, topic.id)

            self.assertListEqual(list(Topic.objects.all()), [])

    def test_sync_valid_topic_empty_description(self):
        topic = TopicFactory(id="1234", title="Test Empty Description", description="")
        self.template_test_sync_one_valid_topic(topic)

    def test_sync_valid_topic_long_id(self):
        topic = create_topic("12345678890")
        self.template_test_sync_one_valid_topic(topic)

    def test_sync_valid_topic_long_description(self):
        topic = TopicFactory(id="1234", title="Test Long Description", description="Lorem ipsum dolor sit amet" * 50)
        self.template_test_sync_one_valid_topic(topic)

    def test_sync_valid_topic_with_subtopic_link_but_no_subtopics(self):
        # Some topics in the API have a subtopics link despite containing no subtopics
        # Given
        topic = create_topic("1234")
        mock_response = Mock(spec=requests.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "items": [
                {
                    "id": topic.id,
                    "title": topic.title,
                    "slug": topic.slug,
                    "description": topic.description,
                    "subtopics_ids": [],
                    "links": {
                        "subtopics": {"href": "topics/1234/subtopics"},
                    },
                }
            ]
        }
        self.mock_requests.get.return_value = mock_response

        # When
        call_command("sync_topics")

        # Then
        self.mock_requests.get.assert_called_once()
        self.assertEqual(Topic.objects.all().count(), 1, "Expect one topic to be saved")
        saved_topic = Topic.objects.first()
        self.assertEqual(saved_topic, topic, "Expect the saved topic to match")

    def test_sync_topic_with_subtopic(self):
        # Given
        root_topic = create_topic("0001")
        subtopic = create_topic("0002")
        mock_root_response = mock_successful_json_response(
            [
                build_topic_api_json(root_topic, subtopics=[subtopic]),
            ]
        )

        mock_subtopic_response = mock_successful_json_response(
            [
                build_topic_api_json(subtopic),
            ]
        )

        # Mock the successive API call responses
        self.mock_requests.get.side_effect = [mock_root_response, mock_subtopic_response]

        # When
        call_command("sync_topics")

        # Then
        self.assertEqual(self.mock_requests.get.call_count, 2, "Expect 2 calls to retrieve topics")
        self.assertEqual(Topic.objects.all().count(), 2, "Expect 2 topics to be saved")
        saved_root_topic = Topic.objects.get(id=root_topic.id)
        saved_subtopic = Topic.objects.get(id=subtopic.id)
        self.assertEqual(saved_root_topic, root_topic, "Expect root topic to match")
        self.assertEqual(saved_subtopic, subtopic, "Expect root topic to match")
        self.assertEqual(
            saved_subtopic.get_parent().id, root_topic.id, "Expect the subtopic to have the correct parent"
        )

    def test_sync_two_root_topics(self):
        # Given
        root_topic = create_topic("0001")
        root_topic_2 = create_topic("0002")
        mock_response = mock_successful_json_response(
            [
                build_topic_api_json(root_topic),
                build_topic_api_json(root_topic_2),
            ]
        )

        # Mock the successive API call responses
        self.mock_requests.get.side_effect = [mock_response]

        # When
        call_command("sync_topics")

        # Then
        self.assertEqual(Topic.objects.all().count(), 2, "Expect 2 topics to be saved")
        saved_root_topic = Topic.objects.get(id=root_topic.id)
        saved_root_topic_2 = Topic.objects.get(id=root_topic_2.id)
        self.assertEqual(saved_root_topic, root_topic, "Expect root topic to match")
        self.assertEqual(saved_root_topic_2, root_topic_2, "Expect root topic to match")

    def test_topics_with_duplicate_titles(self):
        # Duplicate topic titles are valid and do exist
        # Given
        root_topic = TopicFactory(id="0001", title="Duplicated Title")
        subtopic = TopicFactory(id="0002", title=root_topic.title)

        mock_root_topic_response = mock_successful_json_response(
            [
                build_topic_api_json(root_topic, subtopics=[subtopic]),
            ]
        )
        mock_subtopic_response = mock_successful_json_response([build_topic_api_json(subtopic)])

        # Mock the successive API call responses
        self.mock_requests.get.side_effect = [mock_root_topic_response, mock_subtopic_response]

        # When
        call_command("sync_topics")

        # Then
        self.assertEqual(self.mock_requests.get.call_count, 2, "Expect 2 calls to retrieve topics")
        self.assertEqual(Topic.objects.all().count(), 2, "Expect 2 topics to be saved")
        saved_root_topic = Topic.objects.get(id=root_topic.id)
        saved_subtopic = Topic.objects.get(id=subtopic.id)
        self.assertEqual(saved_root_topic, root_topic, "Expect root topic to match")
        self.assertEqual(saved_subtopic, subtopic, "Expect root topic to match")
        self.assertEqual(
            saved_subtopic.get_parent().id, root_topic.id, "Expect the subtopic to have the correct parent"
        )

    def test_update_topic_title(self):
        # Given
        initial_topic = TopicFactory(id="1234", title="Initial Title", description="Test")
        updated_topic = Topic(
            id=initial_topic.id,
            title="Updated Title",
            description=initial_topic.description,
            slug=initial_topic.slug,
        )

        mock_topic_response = mock_successful_json_response([build_topic_api_json(updated_topic)])
        self.mock_requests.get.return_value = mock_topic_response

        # When
        call_command("sync_topics")

        # Then
        self.assertEqual(self.mock_requests.get.call_count, 1, "Expect 1 calls to retrieve topics")
        self.assertEqual(Topic.objects.all().count(), 1, "Expect 1 topics to be saved")
        saved_topic = Topic.objects.get(id=updated_topic.id)
        self.assertEqual(saved_topic.title, updated_topic.title, "Expect topic title to be updated to match")

    def test_update_topic_description(self):
        # Given
        initial_topic = TopicFactory(id="1234", title="Initial Title", description="Test")
        updated_topic = Topic(
            id=initial_topic.id, title=initial_topic.title, description="Updated Description", slug=initial_topic.slug
        )

        mock_topic_response = mock_successful_json_response([build_topic_api_json(updated_topic)])
        self.mock_requests.get.return_value = mock_topic_response

        # When
        call_command("sync_topics")

        # Then
        self.assertEqual(self.mock_requests.get.call_count, 1, "Expect 1 calls to retrieve topics")
        self.assertEqual(Topic.objects.all().count(), 1, "Expect 1 topics to be saved")
        saved_topic = Topic.objects.get(id=updated_topic.id)
        self.assertEqual(
            saved_topic.description, updated_topic.description, "Expect topic description to be updated to match"
        )

    def test_sync_one_topic_no_changes(self):
        # Given
        topic = create_and_save_topic("1234")

        mock_topic_response = mock_successful_json_response([build_topic_api_json(topic)])
        self.mock_requests.get.return_value = mock_topic_response

        # When
        call_command("sync_topics")

        # Then
        self.assertEqual(self.mock_requests.get.call_count, 1, "Expect 1 calls to retrieve topics")
        self.assertEqual(Topic.objects.all().count(), 1, "Expect 1 topics to be saved")
        saved_topic = Topic.objects.get(id=topic.id)
        self.assertEqual(saved_topic, topic, "Expect topic to match")

    def test_removed_topic(self):
        # Given
        topic = Topic(id="1234", title="Initial Title", description="Test")
        Topic.save_new(topic)

        # Mock a response with the topic deleted
        mock_empty_response = mock_successful_json_response([])
        self.mock_requests.get.return_value = mock_empty_response

        # When
        call_command("sync_topics")

        # Then
        self.assertEqual(self.mock_requests.get.call_count, 1, "Expect 1 calls to retrieve topics")
        self.assertEqual(Topic.objects.all().count(), 1, "Expect 1 topics to be saved")
        saved_topic = Topic.objects.get(id=topic.id)
        self.assertTrue(saved_topic.removed, "Expect topic to be marked as removed")

    def test_reinstated_topic(self):
        # Given
        removed_topic = TopicFactory(id="1234", title="Topic Title", removed=True, slug="topic-title")

        # Mock a response with the removed topic re-appearing
        reinstated_topic = Topic(id=removed_topic.id, title=removed_topic.title, removed=False, slug=removed_topic.slug)

        mock_reinstated_response = mock_successful_json_response([build_topic_api_json(reinstated_topic)])
        self.mock_requests.get.return_value = mock_reinstated_response

        # When
        call_command("sync_topics")

        # Then
        self.assertEqual(self.mock_requests.get.call_count, 1, "Expect 1 calls to retrieve topics")
        self.assertEqual(Topic.objects.all().count(), 1, "Expect 1 topics to be saved")

        saved_topic = Topic.objects.get(id=removed_topic.id)
        self.assertFalse(saved_topic.removed, "Expect topic to be marked as removed")

    def test_moved_subtopics(self):
        # Given
        # Create existing topics in the database, with the subtopic as a child of root_topic_1
        root_topic_1 = create_and_save_topic("0001")
        root_topic_2 = create_and_save_topic("0002")
        subtopic = create_and_save_topic("0003", parent_topic=root_topic_1)
        sub_subtopic = create_and_save_topic("0004", parent_topic=subtopic)

        # API response with the subtopic moved from root_topic_1 to root_topic_2
        mock_root_topic_response = mock_successful_json_response(
            [
                build_topic_api_json(root_topic_1),
                build_topic_api_json(root_topic_2, subtopics=[subtopic]),
            ]
        )
        mock_subtopic_response = mock_successful_json_response(
            [build_topic_api_json(subtopic, subtopics=[sub_subtopic])]
        )
        mock_subsubtopic_response = mock_successful_json_response([build_topic_api_json(sub_subtopic)])

        # Mock the successive API call responses
        self.mock_requests.get.side_effect = [
            mock_root_topic_response,
            mock_subtopic_response,
            mock_subsubtopic_response,
        ]

        # When
        call_command("sync_topics")

        # Then
        self.assertEqual(self.mock_requests.get.call_count, 3, "Expect 2 calls to retrieve topics")
        self.assertEqual(Topic.objects.all().count(), 4, "Expect 3 topics to be saved")
        self.assertEqual(
            Topic.objects.get(id=subtopic.id).get_parent().id,
            root_topic_2.id,
            "Expect the subtopic ID to have changed to root topic 2",
        )
        saved_sub_subtopic = Topic.objects.get(id=sub_subtopic.id)
        self.assertEqual(saved_sub_subtopic, sub_subtopic, "Expect sub sub topic to still match")
        self.assertEqual(
            saved_sub_subtopic.get_parent().id,
            subtopic.id,
            "Expect sub subtopic to have moved with it's parent in the tree",
        )

    def test_move_subtopic_to_root(self):
        # Given
        root_topic = create_and_save_topic("0001")
        # Create a topic initially under the root
        initial_subtopic = create_and_save_topic("0002", parent_topic=root_topic)

        # Mock the response with the subtopic moved to the root level
        mock_root_response = mock_successful_json_response(
            [
                build_topic_api_json(root_topic),
                build_topic_api_json(initial_subtopic),
            ]
        )

        # Mock the successive API call responses
        self.mock_requests.get.side_effect = [mock_root_response]

        # When
        call_command("sync_topics")

        # Then
        self.assertEqual(Topic.objects.all().count(), 2, "Expect 2 topics to be saved")
        saved_root_topic = Topic.objects.get(id=root_topic.id)
        saved_moved_topic = Topic.objects.get(id=initial_subtopic.id)
        self.assertEqual(saved_root_topic, root_topic, "Expect root topic to match")
        self.assertEqual(saved_moved_topic, initial_subtopic, "Expect root topic to match")

    def test_move_root_to_subtopic(self):
        # Given
        root_topic = create_and_save_topic("0001")
        root_topic_2 = create_and_save_topic("0002")

        # Mock the response with the one root topic moved under the other
        mock_root_response = mock_successful_json_response(
            [
                build_topic_api_json(root_topic, subtopics=[root_topic_2]),
            ]
        )

        mock_subtopic_response = mock_successful_json_response([build_topic_api_json(root_topic_2)])

        # Mock the successive API call responses
        self.mock_requests.get.side_effect = [mock_root_response, mock_subtopic_response]

        # When
        call_command("sync_topics")

        # Then
        self.assertEqual(self.mock_requests.get.call_count, 2, "Expect 2 calls to retrieve topics")
        self.assertEqual(Topic.objects.all().count(), 2, "Expect 2 topics to be saved")
        saved_moved_topic = Topic.objects.get(id=root_topic_2.id)
        self.assertEqual(
            saved_moved_topic.get_parent().id, root_topic.id, "Expect topic to have moved underneath other root topic"
        )

    def test_initial_response_error(self):
        # Given
        existing_topic = create_and_save_topic("0001")

        mock_response = Mock()
        mock_response.status_code = 500

        # Mock a 500 error scenario
        self.mock_requests.get.return_value.raise_for_status.side_effect = [HTTPError(response=mock_response)]

        # When, then raises
        self.assertRaises(HTTPError, sync_topics.Command().handle)

        # And check the existing topics remain unaffected
        self.assertEqual(Topic.objects.all().count(), 1, "Expect 1 topic to remain in the database")
        saved_topic = Topic.objects.get(id=existing_topic.id)
        self.assertEqual(saved_topic, existing_topic, "Expect existing topic to remain unmodified in database")

    def test_error_response_in_subtopic_call(self):
        # Given
        existing_topic = create_and_save_topic("0001")
        existing_subtopic = create_and_save_topic("0002", parent_topic=existing_topic)

        altered_root_topic = Topic(id=existing_topic.id, title="Altered Title", description=existing_topic.description)

        # Mock a successful first call to get root topics, with a change to the root topic
        mock_root_response = mock_successful_json_response(
            [
                build_topic_api_json(altered_root_topic, subtopics=[existing_subtopic]),
            ]
        )

        # Mock a 500 error on the second, subtopic API call
        mock_error_response = Mock()
        mock_error_response.status_code = 500
        mock_error_response.raise_for_status.side_effect = HTTPError()
        self.mock_requests.get.side_effect = [mock_root_response, mock_error_response]

        # When, then raises
        self.assertRaises(HTTPError, sync_topics.Command().handle)

        # Check the two topics remain unaltered, the changes must be all or nothing
        self.assertEqual(self.mock_requests.get.call_count, 2, "Expect 2 calls to retrieve topics")
        self.assertEqual(Topic.objects.all().count(), 2, "Expect 2 topics to remain in the database")
        saved_root_topic = Topic.objects.get(id=existing_topic.id)
        saved_subtopic = Topic.objects.get(id=existing_subtopic.id)
        self.assertEqual(
            saved_root_topic.title,
            existing_topic.title,
            "Expect the title to match the original existing value, not the updated value",
        )
        self.assertEqual(saved_subtopic, existing_subtopic, "Expect subtopic to remain in database")

    def test_duplicate_topic_id_in_responses(self):
        # Given
        topic = create_topic("0001")
        subtopic = create_topic("0001")

        mock_root_topic_response = mock_successful_json_response(
            [
                build_topic_api_json(topic, subtopics=[subtopic]),
            ]
        )
        mock_subtopic_response = mock_successful_json_response([build_topic_api_json(subtopic)])

        # Mock the successive API call responses
        self.mock_requests.get.side_effect = [mock_root_topic_response, mock_subtopic_response]

        # When, then raises
        self.assertRaises(RuntimeError, sync_topics.Command().handle)


def create_topic(topic_id: str, include_description: bool = True, include_slug: bool = True) -> Topic:
    """Create a topic (without saving it to the database)."""
    topic = Topic(
        id=topic_id,
        title=f"Topic {topic_id}",
    )
    topic.description = f"Description {topic_id}" if include_description else None
    topic.slug = f"topic-{topic_id}" if include_slug else None
    return topic


def create_and_save_topic(topic_id: str, include_description: bool = True, parent_topic: Topic | None = None) -> Topic:
    """Create a topic and save it to the database."""
    topic = create_topic(topic_id, include_description=include_description)
    Topic.save_new(topic, parent_topic=parent_topic)
    return topic


def build_topic_api_json(topic: Topic, subtopics: Iterable[Topic] = ()) -> dict[str, Any]:
    """Return the topic in the format given by the API, with subtopic links."""
    links = {}
    subtopics_ids = []
    for subtopic in subtopics:
        subtopics_ids.append(subtopic.id)
        links["subtopics"] = {"href": f"topics/{topic.id}/subtopics"}
    return {
        "id": topic.id,
        "title": topic.title,
        "description": topic.description,
        "slug": topic.slug,
        "links": links,
        "subtopics_ids": subtopics_ids,
    }


def mock_successful_json_response(topic_json: list[dict[str, Any]]) -> Mock:
    mock_response = Mock(spec=requests.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {"items": topic_json}
    return mock_response
