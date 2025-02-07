from typing import ClassVar

from django.db import models
from django.db.models import UniqueConstraint
from modelcluster.fields import ParentalKey
from treebeard.mp_tree import MP_Node
from wagtail.admin.panels import FieldPanel
from wagtail.search import index


# This is the main 'node' model, it inherits mp_node
# mp_node is short for materialized path, it means the tree has a clear path
class Topic(index.Indexed, MP_Node):
    """A topic model, representing taxonomic topics.
    We use tree nodes to represent the topic/subtopic parent/child relationships.
    """

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

    def __str__(self):
        return self.title_with_depth()

    # this is just a convenience function to make the titles appear with lines
    # eg root | - first child
    def title_with_depth(self):
        if depth := self.get_depth():
            depth_marker = "— " * (depth - 1)
            return depth_marker + self.title
        return self.title

    title_with_depth.short_description = "Title"

    @property
    def parent_title(self):
        if not self.is_root():
            return self.get_parent().title
        return None


class GenericPageToTaxonomyTopic(models.Model):
    """This model enables many-to-many relationships between pages and topics."""

    page = ParentalKey("wagtailcore.Page", related_name="topics")
    topic = models.ForeignKey("taxonomy.Topic", on_delete=models.CASCADE, related_name="generic_pages")

    panels: ClassVar[list[FieldPanel]] = [FieldPanel("topic")]

    class Meta:
        constraints: ClassVar[list[UniqueConstraint]] = [
            UniqueConstraint(fields=["page", "topic"], name="unique_generic_taxonomy")
        ]
