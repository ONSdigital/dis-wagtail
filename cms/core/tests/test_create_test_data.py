from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from cms.core.management.commands.create_test_data import SEEDED_DATA_PREFIX
from cms.images.models import CustomImage
from cms.taxonomy.models import Topic
from cms.topics.models import TopicPage

AFFECTED_MODELS = [TopicPage, Topic, CustomImage]


class CreateTestDataTestCase(TestCase):
    def test_creates_data(self) -> None:
        original_counts = {model: model.objects.count() for model in AFFECTED_MODELS}

        call_command("create_test_data", interactive=False)

        for model, original_count in original_counts.items():
            self.assertGreater(model.objects.count(), original_count, model)

    def test_creates_topics(self) -> None:
        call_command("create_test_data", interactive=False)

        self.assertEqual(TopicPage.objects.count(), 3)
        self.assertEqual(len(set(TopicPage.objects.values_list("title", flat=True))), 3)

        for topic_page in TopicPage.objects.all():
            with self.subTest(topic_page):
                self.assertEqual(
                    [child.block_type for child in topic_page.explore_more], ["internal_link", "external_link"]
                )
                for block in topic_page.explore_more:
                    self.assertIn(SEEDED_DATA_PREFIX, block.value["thumbnail"].title)

    def test_idempotent(self) -> None:
        call_command("create_test_data", interactive=False)
        self.assertEqual(TopicPage.objects.count(), 3)

        call_command("create_test_data", interactive=False)
        self.assertEqual(TopicPage.objects.count(), 3)

    def test_tree_is_valid(self) -> None:
        call_command("create_test_data", interactive=False)

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
        call_command("create_test_data", interactive=False)

        original_counts = {model: model.objects.count() for model in AFFECTED_MODELS}

        output = StringIO()
        call_command("delete_test_data", stdout=output, no_color=True, dry_run=True)
        self.assertIn("Found data to delete", output.getvalue())
        self.assertNotIn("Successfully deleted", output.getvalue())

        for model, original_count in original_counts.items():
            self.assertEqual(model.objects.count(), original_count, model)

    def test_delete_data(self) -> None:
        call_command("create_test_data", interactive=False)

        original_counts = {model: model.objects.count() for model in AFFECTED_MODELS}

        output = StringIO()
        call_command("delete_test_data", stdout=output, no_color=True, interactive=False)
        self.assertIn("Found data to delete", output.getvalue())
        self.assertIn("Successfully deleted", output.getvalue())

        for model, original_count in original_counts.items():
            self.assertLess(model.objects.count(), original_count, model)

    def test_tree_is_valid(self) -> None:
        call_command("create_test_data", interactive=False)

        call_command("delete_test_data", interactive=False, stdout=StringIO())

        output = StringIO()
        call_command("fixtree", interactive=False, stdout=output)

        self.assertIn("Checking page tree for problems...\nNo problems found.", output.getvalue())
        self.assertIn("Checking collection tree for problems...\nNo problems found.", output.getvalue())
