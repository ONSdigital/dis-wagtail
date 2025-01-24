from typing import ClassVar

from django.db import models
from treebeard.mp_tree import MP_Node
from wagtail.search import index


# This is the main 'node' model, it inherits mp_node
# mp_node is short for materialized path, it means the tree has a clear path
class Topic(index.Indexed, MP_Node):
    id = models.CharField(max_length=4, primary_key=True)
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
        depth = "— " * (self.get_depth() - 1)
        return depth + self.title

    title_with_depth.short_description = "Title"

    @property
    def parent_title(self):
        if not self.is_root():
            return self.get_parent().title
        return None
