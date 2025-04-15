from secrets import token_urlsafe
from typing import Any

from django import forms
from django.utils.functional import cached_property
from wagtail.blocks import CharBlock, ListBlock, StructBlock
from wagtail.blocks.struct_block import StructBlockAdapter
from wagtail.telepath import register


class HeadlineFiguresItemBlock(StructBlock):
    """Represents a headline figure."""

    # TODO: make this a hidden value
    figure_id = CharBlock(required=False)
    title = CharBlock(label="Title", max_length=60, required=True)
    figure = CharBlock(label="Figure", max_length=10, required=True)
    supporting_text = CharBlock(label="Supporting text", max_length=100, required=True)

    def clean(self, value: Any) -> dict[str, Any]:
        cleaned_data: dict[str, Any] = super().clean(value)
        # Generate a unique figure_id
        if not cleaned_data["figure_id"]:
            cleaned_data["figure_id"] = token_urlsafe(6)
        return cleaned_data


class HeadlineFiguresBlock(ListBlock):
    """A list of headline figures."""

    def __init__(self, search_index: bool = True, **kwargs: Any) -> None:
        kwargs.setdefault("max_num", 4)
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
