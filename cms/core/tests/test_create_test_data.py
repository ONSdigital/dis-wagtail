from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from cms.core.management.commands.create_test_data import SEEDED_DATA_PREFIX
from cms.topics.models import TopicPage


class CreateTestDataTestCase(TestCase):
    def test_creates_topics(self) -> None:
        call_command("create_test_data", interactive=False)

        self.assertEqual(TopicPage.objects.count(), 6)
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
        self.assertEqual(TopicPage.objects.count(), 6)

        call_command("create_test_data", interactive=False)
        self.assertEqual(TopicPage.objects.count(), 6)

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
        original_topic_page_count = TopicPage.objects.count()

        call_command("create_test_data", interactive=False)
        self.assertGreater(TopicPage.objects.count(), original_topic_page_count)

        output = StringIO()
        call_command("delete_test_data", stdout=output, no_color=True, dry_run=True)
        self.assertIn("Found data to delete", output.getvalue())
        self.assertNotIn("Successfully deleted", output.getvalue())

        self.assertGreater(TopicPage.objects.count(), original_topic_page_count)

    def test_delete_data(self) -> None:
        original_topic_page_count = TopicPage.objects.count()

        call_command("create_test_data", interactive=False)
        self.assertGreater(TopicPage.objects.count(), original_topic_page_count)

        output = StringIO()
        call_command("delete_test_data", stdout=output, no_color=True, interactive=False)
        self.assertIn("Found data to delete", output.getvalue())
        self.assertIn("Successfully deleted", output.getvalue())
        self.assertEqual(TopicPage.objects.count(), original_topic_page_count)

    def test_tree_is_valid(self) -> None:
        call_command("create_test_data", interactive=False)

        call_command("delete_test_data", interactive=False, stdout=StringIO())

        output = StringIO()
        call_command("fixtree", interactive=False, stdout=output)

        self.assertIn("Checking page tree for problems...\nNo problems found.", output.getvalue())
        self.assertIn("Checking collection tree for problems...\nNo problems found.", output.getvalue())
