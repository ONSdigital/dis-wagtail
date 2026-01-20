import typing
from typing import TYPE_CHECKING, Any, ClassVar

from django.db import IntegrityError, models
from django.db.models import UniqueConstraint
from django.utils.functional import cached_property
from modelcluster.fields import ParentalKey
from treebeard.mp_tree import MP_Node, MP_NodeManager
from wagtail.admin.panels import FieldPanel
from wagtail.query import TreeQuerySet
from wagtail.search import index

BASE_TOPIC_DEPTH = 2

if TYPE_CHECKING:
    from django.db.models import BaseConstraint


class TopicManager(MP_NodeManager):
    def get_queryset(self) -> TreeQuerySet:
        """Filter out the dummy root topic from all querysets."""
        # Reuse Wagtail's custom tree QuerySet for helpful utils
        return TreeQuerySet(self.model).order_by("path").filter(depth__gt=1)

    def root_topic(self) -> Topic:
        """Return the dummy root topic."""
        # We create the dummy root in a migration so we know it will exist, so cast to "Topic" for mypy
        return typing.cast(Topic, super().get_queryset().filter(depth=1).get())


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
        ordering = ("path",)

    objects: TopicManager = TopicManager.from_queryset(TreeQuerySet)()

    id = models.CharField(max_length=100, primary_key=True)  # type: ignore[var-annotated]
    title = models.CharField(max_length=100)  # type: ignore[var-annotated]
    slug = models.SlugField(max_length=100)  # type: ignore[var-annotated]
    description = models.TextField(blank=True, null=True)  # type: ignore[var-annotated]
    removed = models.BooleanField(default=False)  # type: ignore[var-annotated]

    node_order_by: ClassVar[list[str]] = ["title"]

    search_fields: ClassVar[list[index.SearchField | index.AutocompleteField]] = [
        index.FilterField("title"),
        index.FilterField("depth"),
        index.SearchField("title"),
        index.AutocompleteField("title"),
    ]

    @classmethod
    def save_new(cls, topic: Topic, parent_topic: Topic | None = None) -> None:
        """Save a new topic either underneath the specific parent if passed, otherwise underneath our default root level
        dummy topic.

        Raises an IntegrityError if a topic with the same ID already exists.
        """
        if Topic.objects.filter(id=topic.id).exists():
            raise IntegrityError(f"Topic with id {topic.id} already exists")
        if not parent_topic:
            parent_topic = Topic.objects.root_topic()
        parent_topic.add_child(instance=topic)

        # we have to save here to force the parent topic object to update, otherwise stale in memory values can cause
        # errors in subsequent actions
        parent_topic.save()

    def get_parent(self, *args: Any, **kwargs: Any) -> Topic | None:
        """Return the parent topic if one exists, or None otherwise.
        Return none if at or below our base topic depth to avoid returning a cached root topic.
        """
        if self.depth <= BASE_TOPIC_DEPTH:
            return None
        return typing.cast(Topic | None, super().get_parent(*args, **kwargs))

    def get_base_parent(self) -> Topic:
        """Return the base level parent topic (top level, with no parent topics), or self if this topic is base depth
        (Excluding the dummy root topic).
        """
        if self.depth == BASE_TOPIC_DEPTH:
            return self
        return typing.cast("Topic", self.get_ancestors().first())

    def move(self, target: Topic | None = None, pos: str = "sorted-child") -> None:
        """Move the topic to underneath the target parent. If no target is passed, move it underneath our root."""
        target_parent = target or Topic.objects.root_topic()
        super().move(target_parent, pos=pos)

    def __str__(self) -> str:
        return str(self.title)

    @property
    def display_parent_topics(self) -> str:
        if ancestors := [topic.title for topic in self.get_ancestors()]:
            return " → ".join(ancestors)
        return ""

    @cached_property
    def slug_path(self) -> str:
        """Return the URL-like path from the root to this topic.
        Used for linking to search listing pages.
        """
        # Ancestors are ordered root to leaf.
        ancestor_slugs = list(self.get_ancestors().values_list("slug", flat=True))
        return "/".join([*ancestor_slugs, self.slug])


class GenericPageToTaxonomyTopic(models.Model):
    """This model enables many-to-many relationships between pages and topics."""

    page = ParentalKey("wagtailcore.Page", related_name="topics")
    topic = models.ForeignKey("taxonomy.Topic", on_delete=models.CASCADE, related_name="related_pages")

    panels: ClassVar[list[FieldPanel]] = [FieldPanel("topic")]

    class Meta:
        constraints: ClassVar[list[BaseConstraint]] = [
            UniqueConstraint(fields=["page", "topic"], name="unique_generic_taxonomy")
        ]
