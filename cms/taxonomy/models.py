from typing import ClassVar, Optional

from django.db import models
from django.db.models import QuerySet, UniqueConstraint
from modelcluster.fields import ParentalKey
from treebeard.mp_tree import MP_Node
from wagtail.admin.panels import FieldPanel
from wagtail.search import index

BASE_TOPIC_DEPTH = 2


class TopicManager(models.Manager):
    def get_queryset(self) -> QuerySet:
        """Filter out the root topic from all querysets."""
        return super().get_queryset().filter(depth__gt=1)

    def root_topic(self) -> "Topic":
        return super().get_queryset().filter(depth=1).first()


# This is the main 'node' model, it inherits mp_node
# mp_node is short for materialized path, it means the tree has a clear path
class Topic(index.Indexed, MP_Node):
    """A topic model, representing taxonomic topics.
    We use tree nodes to represent the topic/subtopic parent/child relationships.

    Note:
    We must be able to cope with topics potentially moving to and from root level. However, Nodes cannot be moved from
    root level in treebeard. To cope with this, we put all topics underneath a dummy root level node. To hide this
    dummy node, we override the default object manager with one which only returns non-root level, actual topic nodes.
    """

    class Meta:
        ordering = ("path", "title")

    objects = TopicManager()  # Override the default manager

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
            parent_topic = Topic.objects.root_topic()
        parent_topic.add_child(instance=self)
        super().save(*args, **kwargs)
        parent_topic.save()

    def get_parent(self, *args, **kwargs) -> Optional["Topic"]:
        """Return the parent topic if one exists, or None otherwise.
        Return none if at or below our base topic depth to avoid returning a cached root topic.
        """
        if self.depth <= BASE_TOPIC_DEPTH:
            return None
        return super().get_parent(*args, **kwargs)

    def move(self, target: Optional["Topic"] = None, **kwargs) -> None:  # pylint: disable=arguments-differ
        """Move the topic to underneath the target parent. If no target is passed, move it underneath our root."""
        if not target:
            return super().move(Topic.objects.root_topic(), **kwargs)
        return super().move(target, **kwargs)

    def __str__(self):
        return self.title_with_depth

    # this is just a convenience function to make the titles appear with lines
    # eg root | - first child
    @property
    def title_with_depth(self) -> str:
        if depth := self.get_depth():
            depth_marker = "—" * (depth - BASE_TOPIC_DEPTH)
            return depth_marker + " " + self.title
        return self.title

    @property
    def parent_title(self) -> str | None:
        if self.get_depth() > BASE_TOPIC_DEPTH:
            return self.get_parent().title
        return None

    @property
    def display_path(self) -> str:
        if ancestors := [topic.title for topic in self.get_ancestors()]:
            return " → ".join(ancestors)
        return ""


class GenericPageToTaxonomyTopic(models.Model):
    """This model enables many-to-many relationships between pages and topics."""

    page = ParentalKey("wagtailcore.Page", related_name="topics")
    topic = models.ForeignKey("taxonomy.Topic", on_delete=models.CASCADE, related_name="related_pages")

    panels: ClassVar[list[FieldPanel]] = [FieldPanel("topic")]

    class Meta:
        constraints: ClassVar[list[UniqueConstraint]] = [
            UniqueConstraint(fields=["page", "topic"], name="unique_generic_taxonomy")
        ]
