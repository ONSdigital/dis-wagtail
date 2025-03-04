from django.db import IntegrityError
from django.test import TestCase
from wagtail.models import Page

from cms.taxonomy.models import GenericPageToTaxonomyTopic, Topic


class TopicModelTest(TestCase):
    def setUp(self):
        self.root_topic = Topic.objects.root_topic()
        self.root_topic_id = "_root"

    def test_get_root_topic(self):
        """Ensure that multiple calls still return the same root topic."""
        root_again = Topic.objects.root_topic()
        self.assertEqual(self.root_topic.id, self.root_topic_id)
        self.assertEqual(root_again.id, self.root_topic.id)
        self.assertEqual(root_again.pk, self.root_topic.pk)
        self.assertEqual(root_again.depth, 1)  # Root node typically has depth=1

    def test_filtered_manager_excludes_root_topic(self):
        """Topic.objects should exclude the dummy root."""
        self.assertNotIn(self.root_topic, Topic.objects.all())

    def test_save_topic_with_no_parent_uses_root_topic(self):
        """If we call Topic.create(...) without specifying parent_topic,
        it will be placed under the dummy root at depth=2.
        """
        t1 = Topic(id="t1", title="First Topic")
        Topic.create(t1)  # no parent passed
        self.assertEqual(t1.depth, 2)  # Root is depth=1, so child is depth=2
        self.assertIsNone(t1.get_parent())

        # Because of the custom manager, we expect to see it in Topic.objects
        self.assertIn(t1, Topic.objects.all())

    def test_save_topic_with_explicit_parent(self):
        """If we call Topic.create(...) with a parent_topic, it will become that node's child."""
        # Create a top-level topic first
        parent_topic = Topic(id="parent-topic", title="Parent Topic")
        Topic.create(parent_topic)

        # Create a child under 'parent_topic'
        child_topic = Topic(id="child-topic", title="Child Topic")
        Topic.create(child_topic, parent_topic=parent_topic)

        self.assertEqual(child_topic.get_parent(), parent_topic)
        self.assertEqual(child_topic.depth, parent_topic.depth + 1)

    def test_move_to_root(self):
        """If we call topic.move(None), it should move under the dummy root."""
        # Create a child under the dummy root
        t1 = Topic(id="t1", title="First Topic")
        Topic.create(t1)

        # Create a child under t1
        t2 = Topic(id="t2", title="Child Topic")
        Topic.create(t2, parent_topic=t1)
        self.assertEqual(t2.get_depth(), 3)
        self.assertEqual(t2.get_parent(), t1)

        # Now move t2 to 'None', which means move to dummy root
        t2.move(None, pos="sorted-child")  # uses our override
        t2.refresh_from_db()
        self.assertIsNone(t2.get_parent())
        self.assertEqual(t2.depth, 2)

    def test_move_to_another_topic(self):
        """Move a topic from one parent to another."""
        # Create two top-level topics
        t1 = Topic(id="t1", title="Topic 1")
        t2 = Topic(id="t2", title="Topic 2")
        Topic.create(t1)
        Topic.create(t2)

        # Create a child under t1
        child = Topic(id="child", title="Child of T1")
        Topic.create(child, parent_topic=t1)
        self.assertEqual(child.get_parent(), t1)
        self.assertEqual(child.depth, 3)

        # Move `child` under t2
        child.move(t2)
        child.refresh_from_db()
        self.assertEqual(child.get_parent(update=True), t2)
        self.assertEqual(child.depth, 3)

    def test_removed_flag_default(self):
        """Ensure 'removed' defaults to False when a Topic is created."""
        t1 = Topic(id="t1", title="Removed Flag Test")
        Topic.create(t1)
        self.assertFalse(t1.removed)

    def test_set_removed_flag(self):
        """Verify we can set the 'removed' flag on a Topic."""
        t1 = Topic(id="t1", title="Topic to Remove")
        Topic.create(t1)
        t1.removed = True
        t1.save()
        t1.refresh_from_db()
        self.assertTrue(t1.removed)

    def test_str_method_returns_title(self):
        """Verify __str__() returns the topic title."""
        t1 = Topic(id="t1", title="Some Topic")
        Topic.create(t1)
        self.assertEqual(str(t1), t1.title)

    def test_id_uniqueness(self):
        """'id' is primary key, so must be unique.
        Attempting to create another Topic with the same id should fail.
        """
        t1 = Topic(id="unique-id", title="Unique Topic")
        Topic.create(t1)
        t2 = Topic(id="unique-id", title="Duplicate Topic")
        with self.assertRaises(IntegrityError):
            Topic.create(t2)

    def test_display_parent_topics(self):
        t1 = Topic(id="t1", title="Topic")
        Topic.create(t1)
        t2 = Topic(id="t2", title="Subtopic")
        Topic.create(t2, parent_topic=t1)
        t3 = Topic(id="t3", title="Second Subtopic")
        Topic.create(t3, parent_topic=t2)

        self.assertEqual(t3.display_parent_topics, "Topic → Subtopic")


class GenericPageToTaxonomyTopicModelTest(TestCase):
    def setUp(self):
        """Set up a root page in Wagtail (usually ID=1 by default)
        and a child page to test relationships with Topics.
        Also get/create the dummy root topic, so we can create normal topics under it.
        """
        self.root_page = Page.objects.get(id=1)
        self.child_page = self.root_page.add_child(instance=Page(title="My Test Page"))
        self.dummy_root = Topic.objects.root_topic()

        # Create some normal topics (depth=2) using save_topic()
        self.topic_a = Topic(id="topic-a", title="Topic A")
        Topic.create(self.topic_a)  # under dummy root
        self.topic_b = Topic(id="topic-b", title="Topic B")
        Topic.create(self.topic_b)

    def test_create_generic_page_to_taxonomy_topic(self):
        """Test creating a valid Page→Topic relationship."""
        link = GenericPageToTaxonomyTopic.objects.create(page=self.child_page, topic=self.topic_a)
        self.assertEqual(GenericPageToTaxonomyTopic.objects.count(), 1)
        self.assertEqual(link.page, self.child_page)
        self.assertEqual(link.topic, self.topic_a)

    def test_unique_constraint_for_page_topic(self):
        """Test that you cannot create two GenericPageToTaxonomyTopic
        with the same (page, topic) pair.
        """
        GenericPageToTaxonomyTopic.objects.create(page=self.child_page, topic=self.topic_a)
        with self.assertRaises(IntegrityError):
            GenericPageToTaxonomyTopic.objects.create(page=self.child_page, topic=self.topic_a)

    def test_multiple_different_topics_on_same_page(self):
        """You can attach multiple distinct topics to the same page.
        This should not violate the uniqueness constraint.
        """
        link_a = GenericPageToTaxonomyTopic.objects.create(page=self.child_page, topic=self.topic_a)
        link_b = GenericPageToTaxonomyTopic.objects.create(page=self.child_page, topic=self.topic_b)
        self.assertEqual(GenericPageToTaxonomyTopic.objects.count(), 2)
        self.assertNotEqual(link_a.topic, link_b.topic)

    def test_same_topic_on_different_pages(self):
        """You can attach the same topic to different pages."""
        another_page = self.root_page.add_child(instance=Page(title="Another Page"))
        link_1 = GenericPageToTaxonomyTopic.objects.create(page=self.child_page, topic=self.topic_a)
        link_2 = GenericPageToTaxonomyTopic.objects.create(page=another_page, topic=self.topic_a)
        self.assertEqual(GenericPageToTaxonomyTopic.objects.count(), 2)
        self.assertNotEqual(link_1.page, link_2.page)
        self.assertEqual(link_1.topic, link_2.topic)

    def test_delete_topic_cascades(self):
        """If a Topic is deleted, the GenericPageToTaxonomyTopic linking it
        should also be deleted (because of on_delete=models.CASCADE).
        """
        link = GenericPageToTaxonomyTopic.objects.create(page=self.child_page, topic=self.topic_a)
        self.topic_a.delete()  # This should cascade-delete the link
        self.assertFalse(GenericPageToTaxonomyTopic.objects.filter(pk=link.pk).exists())
