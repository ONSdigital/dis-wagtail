import itertools
import json
from io import StringIO

from django.core.management import call_command
from django.db.models.signals import post_save
from django.test import TestCase
from django.test.testcases import SimpleTestCase
from modelsearch.index import class_is_indexed
from wagtail.models import ReferenceIndex

from cms.datasets.models import Dataset
from cms.images.models import CustomImage
from cms.taxonomy.models import Topic
from cms.test_data.config import TestDataConfig
from cms.test_data.management.commands.create_test_data import SEEDED_DATA_PREFIX
from cms.topics.models import TopicPage

AFFECTED_MODELS = [TopicPage, Topic, CustomImage, Dataset]


class CreateTestDataTestCase(TestCase):
    def _call_with_config(self, config: dict | None = None) -> str:
        output = StringIO()
        call_command(
            "create_test_data", interactive=False, stdout=output, config=TestDataConfig.model_validate(config or {})
        )
        return output.getvalue()

    def test_creates_data(self) -> None:
        original_counts = {model: model.objects.count() for model in AFFECTED_MODELS}

        self._call_with_config()

        for model, original_count in original_counts.items():
            with self.subTest(model):
                self.assertGreater(model.objects.count(), original_count, model)

    def test_creates_topics(self) -> None:
        self.assertEqual(TopicPage.objects.count(), 0)
        self._call_with_config(
            {
                "topics": {
                    "count": 3,
                    "datasets": 1,
                    "dataset_manual_links": 1,
                    "explore_more": 2,
                    "published": 1,
                    "revisions": {"min": 1, "max": 3},
                }
            }
        )
        self.assertEqual(TopicPage.objects.filter(alias_of_id=None).count(), 3)
        self.assertEqual(TopicPage.objects.exclude(alias_of_id=None).count(), 3)
        self.assertEqual(len(set(TopicPage.objects.values_list("title", flat=True))), 3)

        for topic_page in TopicPage.objects.filter(alias_of_id=None):
            with self.subTest(topic_page):
                self.assertEqual(
                    [child.block_type for child in topic_page.explore_more], ["internal_link", "external_link"]
                )
                for block in topic_page.explore_more:
                    self.assertIn(SEEDED_DATA_PREFIX, block.value["thumbnail"].title)

                self.assertLessEqual(topic_page.revisions.count(), 3)
                self.assertGreaterEqual(topic_page.revisions.count(), 1)

                self.assertTrue(topic_page.live)

    def test_idempotent(self) -> None:
        self._call_with_config()

        topic_titles = set(TopicPage.objects.values_list("title", flat=True))

        self.assertEqual(TopicPage.objects.count(), 6)

        self._call_with_config()
        self.assertEqual(TopicPage.objects.count(), 6)
        self.assertEqual(set(TopicPage.objects.values_list("title", flat=True)), topic_titles)

    def test_seeded(self) -> None:
        self._call_with_config()

        topic_titles = set(TopicPage.objects.values_list("title", flat=True))

        call_command("delete_test_data", stdout=StringIO(), interactive=False)

        self._call_with_config()

        self.assertEqual(set(TopicPage.objects.values_list("title", flat=True)), topic_titles)

    def test_tree_is_valid(self) -> None:
        self._call_with_config()

        output = StringIO()
        call_command("fixtree", interactive=False, stdout=output)

        self.assertIn("Checking page tree for problems...\nNo problems found.", output.getvalue())
        self.assertIn("Checking collection tree for problems...\nNo problems found.", output.getvalue())


class DeleteTestDataTestCase(TestCase):
    def test_no_existing_data(self) -> None:
        output = StringIO()
        call_command("delete_test_data", stdout=output, no_color=True)
        self.assertIn("No data to delete", output.getvalue())

    def test_dry_run(self) -> None:
        call_command("create_test_data", interactive=False, config=TestDataConfig(), stdout=StringIO())

        original_counts = {model: model.objects.count() for model in AFFECTED_MODELS}

        output = StringIO()
        call_command("delete_test_data", stdout=output, no_color=True, dry_run=True)
        self.assertIn("Found data to delete", output.getvalue())
        self.assertNotIn("Successfully deleted", output.getvalue())

        for model, original_count in original_counts.items():
            self.assertEqual(model.objects.count(), original_count, model)

    def test_delete_data(self) -> None:
        call_command("create_test_data", interactive=False, config=TestDataConfig(), stdout=StringIO())

        original_counts = {model: model.objects.count() for model in AFFECTED_MODELS}

        output = StringIO()
        call_command("delete_test_data", stdout=output, no_color=True, interactive=False)
        self.assertIn("Found data to delete", output.getvalue())
        self.assertIn("Successfully deleted", output.getvalue())

        for model, original_count in original_counts.items():
            self.assertLess(model.objects.count(), original_count, model)

    def test_tree_is_valid(self) -> None:
        call_command("create_test_data", interactive=False, config=TestDataConfig(), stdout=StringIO())

        call_command("delete_test_data", interactive=False, stdout=StringIO())

        output = StringIO()
        call_command("fixtree", interactive=False, stdout=output)

        self.assertIn("Checking page tree for problems...\nNo problems found.", output.getvalue())
        self.assertIn("Checking collection tree for problems...\nNo problems found.", output.getvalue())

        # Topics aren't part of the page tree, to manually check they're valid
        self.assertEqual(Topic.objects.root_topic().numchild, 0)
        self.assertEqual(Topic.find_problems(), ([], [], [], [], []))

    def test_deletes_reference_index(self):
        call_command("create_test_data", interactive=False, config=TestDataConfig(), stdout=StringIO())

        instances = list(
            itertools.chain.from_iterable(
                model.objects.all() for model in AFFECTED_MODELS if ReferenceIndex.model_is_indexable(model)
            )
        )

        call_command("delete_test_data", interactive=False, stdout=StringIO())

        for instance in instances:
            self.assertFalse(ReferenceIndex.get_references_for_object(instance).exists())
            self.assertFalse(ReferenceIndex.get_references_to(instance).exists())

    def test_deletes_search_index(self):
        call_command("create_test_data", interactive=False, config=TestDataConfig(), stdout=StringIO())

        instances = list(
            itertools.chain.from_iterable(model.objects.all() for model in AFFECTED_MODELS if class_is_indexed(model))
        )

        call_command("delete_test_data", interactive=False, stdout=StringIO())

        for instance in instances:
            self.assertFalse(instance.index_entries.exists())

    def test_signals_reconnected(self):
        call_command("create_test_data", interactive=False, config=TestDataConfig(), stdout=StringIO())

        post_save_receivers = len(post_save.receivers)

        call_command("delete_test_data", interactive=False, stdout=StringIO())

        self.assertEqual(len(post_save.receivers), post_save_receivers)


class ShowDefaultTestDataConfigTestCase(SimpleTestCase):
    def test_output_default(self) -> None:
        output = StringIO()
        call_command("show_default_test_data_config", stdout=output)

        default_config = TestDataConfig.model_validate_json(output.getvalue())
        self.assertEqual(default_config, TestDataConfig())

    def test_outputs_schema(self) -> None:
        output = StringIO()
        call_command("show_default_test_data_config", stdout=output, schema=True)

        # We can't really validate it, so just check it looks like JSON
        json.loads(output.getvalue())
