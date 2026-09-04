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

from cms.core.db_router import force_write_db_for

# The dummy root sits at depth 1 and real topics start below it, so every depth comparison in this module
# is offset by one level that users never see.
DUMMY_ROOT_DEPTH = 1
BASE_TOPIC_DEPTH = 2

if TYPE_CHECKING:
    from django.db.models import BaseConstraint


class TopicManager(MP_NodeManager):
    def get_queryset(self) -> TreeQuerySet:
        """Return every row, dummy root included.

        This must not filter. Treebeard resolves the tree through `cls.objects` by name, in roughly twenty
        places, and offers no hook to point it at a different manager. Hiding the dummy root here makes it
        invisible to add_child, move, get_root_nodes and the rest, which then fail with Topic.DoesNotExist.

        Anything that shows or enumerates topics wants `topics()` below instead.
        """
        # Reuse Wagtail's custom tree QuerySet for helpful utils
        return TreeQuerySet(self.model, using=self._db, hints=self._hints).order_by("path")

    def topics(self) -> TreeQuerySet:
        """Return the real topics, excluding the dummy root."""
        return self.get_queryset().filter(depth__gt=DUMMY_ROOT_DEPTH)

    def root_topic(self) -> Topic:
        """Return the dummy root topic."""
        # We create the dummy root in a migration so we know it will exist, so cast to "Topic" for mypy
        return typing.cast(Topic, self.get_queryset().filter(depth=DUMMY_ROOT_DEPTH).get())


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

    search_auto_update = True

    class Meta:
        ordering = ("path",)

    objects: TopicManager = TopicManager.from_queryset(TreeQuerySet)()

    id = models.CharField(max_length=100, primary_key=True)
    title = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100)
    description = models.TextField(blank=True, null=True)
    removed = models.BooleanField(default=False)

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
        # Ancestors are ordered root to leaf, so without dropping the dummy root this would return it.
        return typing.cast("Topic", self.get_topic_ancestors().first())

    def move(self, target: Topic | None = None, pos: str = "sorted-child") -> None:
        """Move the topic to underneath the target parent. If no target is passed, move it underneath our root."""
        target_parent = target or Topic.objects.root_topic()
        super().move(target_parent, pos=pos)

    def __str__(self) -> str:
        return str(self.title)

    def get_topic_ancestors(self) -> models.QuerySet[Topic]:
        """Return the ancestors a user would recognise, without the dummy root.

        get_ancestors goes through cls.objects, which cannot filter the dummy root out, so anything walking
        up the tree for display has to drop it here instead.
        """
        # treebeard is untyped, so get_ancestors() comes back as Any
        return typing.cast("models.QuerySet[Topic]", self.get_ancestors().filter(depth__gt=DUMMY_ROOT_DEPTH))

    @property
    def display_parent_topics(self) -> str:
        if ancestors := [topic.title for topic in self.get_topic_ancestors()]:
            return " → ".join(ancestors)
        return ""

    @cached_property
    def slug_path(self) -> str:
        """Return the URL-like path from the root to this topic.
        Used for linking to search listing pages.
        """
        # Ancestors are ordered root to leaf.
        ancestor_slugs = list(self.get_topic_ancestors().values_list("slug", flat=True))
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

    def save(self, **kwargs: Any) -> None:
        """Silently deduplicates when modelcluster tries to INSERT a (page, topic) pair that was already
        committed by a concurrent save/session.
        Revisit when https://github.com/wagtail/wagtail/issues/14359 is addressed.
        """
        if not kwargs.get("force_insert") and self._state.adding and self.page_id and self.topic_id:
            existing_pk = (
                force_write_db_for(GenericPageToTaxonomyTopic.objects)
                .filter(page_id=self.page_id, topic_id=self.topic_id)
                .values_list("pk", flat=True)
                .first()
            )
            if existing_pk is not None:
                self.pk = existing_pk
                self._state.adding = False

        super().save(**kwargs)
