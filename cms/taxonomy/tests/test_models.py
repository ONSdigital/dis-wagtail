import unittest

from django.db import IntegrityError
from django.test import TestCase
from wagtail.models import Page

from cms.taxonomy.models import Topic, GenericPageToTaxonomyTopic


class TopicModelTest(TestCase):
    def test_create_root_topic(self):
        root_topic = Topic.add_root(id="root", title="Root Topic")
        self.assertEqual(Topic.objects.count(), 1)
        self.assertEqual(root_topic.title, "Root Topic")
        self.assertTrue(root_topic.is_root())

    def test_create_child_topic(self):
        root_topic = Topic.add_root(id="root", title="Root Topic")
        child_topic = root_topic.add_child(id="child", title="Child Topic")
        self.assertEqual(child_topic.get_parent(), root_topic)
        self.assertFalse(child_topic.is_root())
        self.assertEqual(child_topic.title_with_depth(), "— Child Topic")
        self.assertEqual(child_topic.parent_title, "Root Topic")

    def test_title_with_depth_on_root(self):
        root_topic = Topic.add_root(id="root", title="Root Topic")
        self.assertEqual(root_topic.title_with_depth(), "Root Topic")
        self.assertIsNone(root_topic.parent_title)

    def test_removed_flag_default(self):
        root_topic = Topic.add_root(id="root", title="Root Topic")
        # self.assertFalse(root_topic.removed)
        print(root_topic)
        breakpoint()


class GenericPageToTaxonomyTopicModelTest(TestCase):
    def setUp(self):
        # Create a root page for demonstration
        self.root_page = Page.objects.get(id=1)  # Usually the default Wagtail root page in a test DB
        # Create a normal Wagtail Page (or a custom page type) under root
        self.child_page = self.root_page.add_child(instance=Page(title="Child Page"))

        # Create a Topic
        self.root_topic = Topic.add_root(id="topic-1", title="Topic 1")

    def test_create_generic_page_to_taxonomy_topic(self):
        link = GenericPageToTaxonomyTopic.objects.create(page=self.child_page, topic=self.root_topic)
        self.assertEqual(GenericPageToTaxonomyTopic.objects.count(), 1)
        self.assertEqual(link.page, self.child_page)
        self.assertEqual(link.topic, self.root_topic)

    def test_unique_constraint(self):
        """Test that you cannot create two GenericPageToTaxonomyTopic with the same page/topic pair."""
        GenericPageToTaxonomyTopic.objects.create(page=self.child_page, topic=self.root_topic)
        with self.assertRaises(IntegrityError):
            GenericPageToTaxonomyTopic.objects.create(page=self.child_page, topic=self.root_topic)
