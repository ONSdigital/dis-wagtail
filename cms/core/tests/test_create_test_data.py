from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from cms.topics.models import TopicPage


class CreateTestDataTestCase(TestCase):
    def test_creates_topics(self) -> None:
        call_command(
            "create_test_data",
        )

        self.assertEqual(TopicPage.objects.count(), 6)
        self.assertEqual(len(set(TopicPage.objects.values_list("title", flat=True))), 3)

    def test_idempotent(self) -> None:
        call_command(
            "create_test_data",
        )
        self.assertEqual(TopicPage.objects.count(), 6)

        call_command(
            "create_test_data",
        )
        self.assertEqual(TopicPage.objects.count(), 3)


class DeleteTestDataTestCase(TestCase):
    def test_no_existing_data(self) -> None:
        output = StringIO()
        call_command("delete_test_data", stdout=output, no_color=True)
        self.assertIn("No data to delete", output.getvalue())

    def test_dry_run(self) -> None:
        original_topic_page_count = TopicPage.objects.count()

        call_command(
            "create_test_data",
        )
        self.assertGreater(TopicPage.objects.count(), original_topic_page_count)

        output = StringIO()
        call_command("delete_test_data", stdout=output, no_color=True, dry_run=True)
        self.assertIn("Found data to delete", output.getvalue())
        self.assertNotIn("Successfully deleted", output.getvalue())

        self.assertGreater(TopicPage.objects.count(), original_topic_page_count)

    def test_delete_data(self) -> None:
        original_topic_page_count = TopicPage.objects.count()

        call_command(
            "create_test_data",
        )
        self.assertGreater(TopicPage.objects.count(), original_topic_page_count)

        output = StringIO()
        call_command("delete_test_data", stdout=output, no_color=True, interactive=False)
        self.assertIn("Found data to delete", output.getvalue())
        self.assertIn("Successfully deleted", output.getvalue())
        self.assertEqual(TopicPage.objects.count(), original_topic_page_count)
