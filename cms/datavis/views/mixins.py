from collections.abc import Sequence
from typing import TYPE_CHECKING

from django.urls import reverse
from django.utils.functional import cached_property
from wagtail.admin.ui.components import MediaContainer
from wagtail.admin.ui.side_panels import ChecksSidePanel

if TYPE_CHECKING:
    from django.utils.functional import Promise


class RemoveChecksSidePanelMixin:
    """A mixin for custom create/edit/copy views that removes the `ChecksSidePanel` that Wagtail
    adds automatically for previewable snippets.
    """

    def get_side_panels(self) -> "MediaContainer":
        return MediaContainer(
            [
                panel
                for panel in super().get_side_panels()  # type: ignore[misc]
                if not isinstance(panel, ChecksSidePanel)
            ]
        )


class RemoveSnippetIndexBreadcrumbItemMixin:
    """A mixin for custom views that removes the breadcrumb item linking to the Snippet index."""

    @cached_property
    def snippets_index_url(self) -> str:
        return reverse("wagtailsnippets:index")

    def get_breadcrumbs_items(self) -> Sequence[dict[str, "str | Promise"]]:
        return [
            item
            for item in super().get_breadcrumbs_items()  # type: ignore[misc]
            if item["url"] != str(self.snippets_index_url)
        ]
