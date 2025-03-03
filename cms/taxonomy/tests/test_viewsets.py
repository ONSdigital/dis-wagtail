from django.test import TestCase
from django.urls import reverse
from wagtail.models import Page
from wagtail.test.utils import WagtailTestUtils

from cms.taxonomy.models import Topic
from cms.taxonomy.viewsets import (
    ExclusiveTopicChooserViewSet,
    TopicChooserViewSet,
)
from cms.themes.models import ThemePage
from cms.topics.models import TopicPage


class TestTopicChooserViewSet(TestCase, WagtailTestUtils):
    """Tests for the default TopicChooserViewSet."""

    @classmethod
    def setUpTestData(cls):
        cls.superuser = cls.create_superuser(username="admin")

        cls.list_url = reverse("topic_chooser:choose")

    def setUp(self):
        self.client.force_login(self.superuser)

        # Ensure dummy root exists
        self.root_topic = Topic.objects.root_topic()

        # Create some normal topics under the dummy root
        self.topic_a = Topic(id="topic-a", title="Topic A")
        self.topic_a.save_new_topic()

        self.topic_b = Topic(id="topic-b", title="Topic B")
        self.topic_b.save_new_topic()

        self.topic_c = Topic(id="topic-c", title="Topic C")
        self.topic_c.save_new_topic(parent_topic=self.topic_b)

        self.topic_d = Topic(id="topic-d", title="Topic D")
        self.topic_d.save_new_topic(parent_topic=self.topic_c)

    def test_viewset_attributes(self):
        """Basic checks for the text attributes that define how the chooser UI gets labeled."""
        viewset = TopicChooserViewSet("topic_chooser")

        self.assertEqual(viewset.name, "topic_chooser")
        self.assertEqual(viewset.choose_one_text, "Choose a topic")
        self.assertEqual(viewset.choose_another_text, "Choose a different topic")
        self.assertEqual(viewset.icon, "tag")

    def test_admin_chooser_list_view(self):
        """Integration-style test that checks the actual chooser list URL,
        ensuring that the expected topics appear in the HTML response.
        """
        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, 200)

        self.assertContains(response, "Title")
        self.assertContains(response, "Parent Topics")
        self.assertContains(response, "Topic A")
        self.assertContains(response, "Topic B")
        self.assertContains(response, "Topic C")
        self.assertContains(response, "Topic D")
        self.assertContains(response, "Topic B \\u2192 Topic C")


class TestExclusiveTopicChooserViewSet(TestCase, WagtailTestUtils):
    """Tests the ExclusiveTopicChooserViewSet, verifying that its get_object_list()
    excludes topics in use by theme or topic pages.
    """

    @classmethod
    def setUpTestData(cls):
        cls.superuser = cls.create_superuser(username="admin")

        cls.list_url = reverse("exclusive_topic_chooser:choose")

    def setUp(self):
        self.client.force_login(self.superuser)

        # Wagtail root page
        self.root_page = Page.objects.get(pk=1)

        # Ensure the dummy root topic is created
        self.root_topic = Topic.objects.root_topic()

        # Create two normal topics
        self.topic_x = Topic(id="topic-x", title="Topic X")
        self.topic_x.save_new_topic()
        self.topic_y = Topic(id="topic-y", title="Topic Y")
        self.topic_y.save_new_topic()

    def test_viewset_attributes(self):
        """Basic checks for the text attributes that define how the chooser UI gets labeled."""
        viewset = ExclusiveTopicChooserViewSet("exclusive_topic_chooser")

        self.assertEqual(viewset.name, "exclusive_topic_chooser")
        self.assertEqual(viewset.choose_one_text, "Choose a topic")
        self.assertEqual(viewset.choose_another_text, "Choose a different topic")
        self.assertEqual(viewset.icon, "tag")

    def test_register_widget_false(self):
        """Exclusive chooser shouldn't register its widget by default."""
        viewset = ExclusiveTopicChooserViewSet("exclusive_topic_chooser")

        self.assertFalse(viewset.register_widget)

    def test_register_widget_true(self):
        """Exclusive chooser should register its widget when register_widget is set to True."""
        viewset = ExclusiveTopicChooserViewSet("exclusive_topic_chooser")

        self.assertTrue(viewset.widget_class)

    def test_get_object_list_excludes_linked_topic_theme_page(self):
        """Create a real ThemePage referencing topic_x, ensuring it is excluded
        by get_object_list().
        """
        theme_page = ThemePage(title="My Theme", topic=self.topic_x, summary="My theme page summary")
        self.root_page.add_child(instance=theme_page)
        theme_page.save()

        viewset = ExclusiveTopicChooserViewSet("exclusive_topic_chooser")
        queryset = viewset.get_object_list()

        self.assertNotIn(self.topic_x, queryset)
        self.assertIn(self.topic_y, queryset)
        self.assertEqual(queryset.count(), 1)

    def test_get_object_list_excludes_linked_topic_topic_page(self):
        """Create a real TopicPage referencing topic_x, ensuring it is excluded
        by get_object_list().
        """
        topic_page = TopicPage(title="My Topic", topic=self.topic_x, summary="My topic page summary")
        self.root_page.add_child(instance=topic_page)
        topic_page.save()

        viewset = ExclusiveTopicChooserViewSet("exclusive_topic_chooser")
        queryset = viewset.get_object_list()

        self.assertNotIn(self.topic_x, queryset)
        self.assertIn(self.topic_y, queryset)
        self.assertEqual(queryset.count(), 1)

    def test_admin_chooser_list_excludes_linked_topic_integration_theme_page(self):
        """Theme Page: Integration test that calls the real Wagtail route, verifying the output
        does not contain the linked topic in the HTML.
        """
        theme_page = ThemePage(title="My Theme", topic=self.topic_x, summary="My theme page summary")
        self.root_page.add_child(instance=theme_page)
        theme_page.save()

        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 200)

        self.assertNotContains(response, "Topic X")
        self.assertContains(response, "Topic Y")

    def test_admin_chooser_list_excludes_linked_topic_integration_topic_page(self):
        """Topic Page: Integration test that calls the real Wagtail route, verifying the output
        does not contain the linked topic in the HTML.
        """
        topic_page = TopicPage(title="My Topic", topic=self.topic_x, summary="My topic page summary")
        self.root_page.add_child(instance=topic_page)
        topic_page.save()

        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 200)

        self.assertNotContains(response, "Topic X")
        self.assertContains(response, "Topic Y")
