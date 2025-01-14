from collections.abc import Iterator
from typing import TYPE_CHECKING, Any

from django.db import models
from django.forms import Media

from cms.datavis.blocks import DataVisBlock

if TYPE_CHECKING:
    from django.http import HttpRequest
    from wagtail.blocks.stream_block import StreamValue

    from cms.datavis.models import Visualisation


class VisualisationsPageMixin(models.Model):
    """A mixin for Wagtail pages that can include visualisations in
    their 'content' StreamField.

    The purpose if this mixin is to gather all of the media used by
    potential visualisations into a `django.forms.Media` object, to
    avoid duplication, and to allow <style> and <script> tags to be
    rendered together in a dedicated place in the page template.
    """

    class Meta:
        abstract = True

    def get_visualisations(self) -> Iterator["Visualisation"]:
        content: StreamValue = self.content  # type: ignore[attr-defined]
        for bound_block in content:
            if isinstance(bound_block.block, DataVisBlock):
                yield bound_block.value["visualisation"].specific

    def get_visualisation_media(self, request: "HttpRequest") -> Media:
        """Return all media required to successfully render all of the
        visualisations featured on this page.
        """
        media = Media()
        for visualisation in self.get_visualisations():
            media += visualisation.media
        return media

    def get_extra_media(self, request: "HttpRequest") -> Media:
        """Return all additional media required to render the page
        successfully. By default, this just includes media featured
        on the page, but could by extended to include form media
        or media or media from other block types.
        """
        return self.get_visualisation_media(request)

    def get_context(self, request: "HttpRequest", *args: Any, **kwargs: Any) -> dict[str, Any]:
        """Overrides ``Page.get_context()`` to include 'extra_media'
        in the context, which can be used to render a deduplicated
        set of extra <style> and <script> tags in the page template.
        """
        context = super().get_context(request, *args, **kwargs)  # type: ignore[misc]
        context["extra_media"] = self.get_extra_media(request)
        return context
