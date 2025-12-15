from django.core.management import call_command
from django.test import TestCase

from cms.topics.models import TopicPage


class CreateTestDataTestCase(TestCase):
    def test_creates_topics(self) -> None:
        call_command(
            "create_test_data",
        )

        self.assertEqual(TopicPage.objects.count(), 3)
        self.assertEqual(len(set(TopicPage.objects.values_list("title", flat=True))), 3)

    def test_idempotent(self) -> None:
        call_command(
            "create_test_data",
        )
        self.assertEqual(TopicPage.objects.count(), 3)

        call_command(
            "create_test_data",
        )
        self.assertEqual(TopicPage.objects.count(), 3)
