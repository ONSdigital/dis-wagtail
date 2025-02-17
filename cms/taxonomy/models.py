from typing import ClassVar, Optional

from django.db import models
from django.db.models import QuerySet, UniqueConstraint
from modelcluster.fields import ParentalKey
from treebeard.mp_tree import MP_Node
from wagtail.admin.panels import FieldPanel
from wagtail.search import index

ROOT_TOPIC_DATA = {"id": "_root", "title": "Root Topic", "description": "Dummy root topic"}
BASE_TOPIC_DEPTH = 2


class TopicManager(models.Manager):
    def get_queryset(self) -> QuerySet:
        """Filter out the root topic from all querysets."""
        return super().get_queryset().filter(depth__gt=1)


# This is the main 'node' model, it inherits mp_node
# mp_node is short for materialized path, it means the tree has a clear path
class Topic(index.Indexed, MP_Node):
    """A topic model, representing taxonomic topics.
    We use tree nodes to represent the topic/subtopic parent/child relationships.
    """

    objects = TopicManager()  # Override the default manager
    all_objects = models.Manager()  # Keep the default manager so we can still access the root topic

    id = models.CharField(max_length=100, primary_key=True)
    title = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    removed = models.BooleanField(default=False)

    node_order_by: ClassVar[list[str]] = ["title"]

    search_fields: ClassVar[list[index.SearchField | index.AutocompleteField]] = [
        index.FilterField("title"),
        index.FilterField("depth"),
        index.SearchField("title"),
        index.AutocompleteField("title"),
    ]

    def save_topic(self, *args, parent_topic: Optional["Topic"] = None, **kwargs) -> None:
        """Save a topic either underneath the specific parent if passed, otherwise underneath our default root level
        dummy topic.
        """
        if not parent_topic:
            parent_topic = self.get_or_create_root_topic()
        parent_topic.add_child(instance=self)
        super().save(*args, **kwargs)
        parent_topic.save()

    def get_parent(self, *args, **kwargs) -> Optional["Topic"]:
        """Return the parent topic if one exists, or None otherwise."""
        try:
            return super().get_parent(*args, **kwargs)
        except Topic.DoesNotExist:
            return None

    def move(self, target: Optional["Topic"], **kwargs):  # pylint: disable=arguments-differ
        if not target:
            return super().move(self.get_or_create_root_topic(), **kwargs)
        return super().move(target, **kwargs)

    def __str__(self):
        return self.title_with_depth()

    @classmethod
    def get_or_create_root_topic(cls) -> "Topic":
        if root_topic := cls.all_objects.filter(id=ROOT_TOPIC_DATA["id"]).first():
            return root_topic
        root_topic = Topic.add_root(instance=Topic(**ROOT_TOPIC_DATA))
        return root_topic

    # this is just a convenience function to make the titles appear with lines
    # eg root | - first child
    def title_with_depth(self) -> str:
        if depth := self.get_depth():
            depth_marker = "— " * (depth - BASE_TOPIC_DEPTH)
            return depth_marker + self.title
        return self.title

    title_with_depth.short_description = "Title"

    @property
    def parent_title(self) -> str | None:
        if self.get_depth() > BASE_TOPIC_DEPTH:
            return self.get_parent().title
        return None


class GenericPageToTaxonomyTopic(models.Model):
    """This model enables many-to-many relationships between pages and topics."""

    page = ParentalKey("wagtailcore.Page", related_name="topics")
    topic = models.ForeignKey("taxonomy.Topic", on_delete=models.CASCADE, related_name="related_pages")

    panels: ClassVar[list[FieldPanel]] = [FieldPanel("topic")]

    class Meta:
        constraints: ClassVar[list[UniqueConstraint]] = [
            UniqueConstraint(fields=["page", "topic"], name="unique_generic_taxonomy")
        ]
