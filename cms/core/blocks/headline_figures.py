from typing import Any

from django import forms
from django.utils.functional import cached_property
from wagtail.blocks import CharBlock, ListBlock, StructBlock
from wagtail.blocks.struct_block import StructBlockAdapter
from wagtail.telepath import register


class HeadlineFiguresItemBlock(StructBlock):
    """Represents a headline figure."""

    figure_id = CharBlock(required=False)
    title = CharBlock(label="Title", required=True)
    figure = CharBlock(label="Figure", required=True)
    supporting_text = CharBlock(label="Supporting text", required=True)

    class Meta:
        # The help_text may be updated via JavaScript
        help_text = "Enter the headline figure details."


class HeadlineFiguresBlock(ListBlock):
    """A list of headline figures."""

    def __init__(self, search_index: bool = True, **kwargs: Any) -> None:
        kwargs.setdefault("max_num", 6)
        super().__init__(HeadlineFiguresItemBlock, search_index=search_index, **kwargs)

    class Meta:
        icon = "data-analysis"
        label = "Headline figures"
        template = "templates/components/streamfield/headline_figures_block.html"


class HeadlineFiguresItemBlockAdapter(StructBlockAdapter):
    js_constructor = "cms.core.widgets.HeadlineFiguresItemBlock"

    @cached_property
    def media(self) -> forms.Media:
        parent_js = super().media._js  # pylint: disable=protected-access
        return forms.Media(js=[*parent_js, "js/blocks/headline-figures-item-block.js"])


register(HeadlineFiguresItemBlockAdapter(), HeadlineFiguresItemBlock)
