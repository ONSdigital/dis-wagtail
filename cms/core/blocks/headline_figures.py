from django import forms
from django.utils.functional import cached_property
from wagtail.admin.telepath import register
from wagtail.blocks import CharBlock, StructBlock
from wagtail.blocks.struct_block import StructBlockAdapter


class HeadlineFiguresItemBlock(StructBlock):
    """Represents a headline figure."""

    figure_id = CharBlock(required=False)
    title = CharBlock(label="Title", required=True, max_length=255)
    figure = CharBlock(label="Figure", required=True, max_length=255)
    supporting_text = CharBlock(label="Supporting text", required=True, max_length=255)

    class Meta:
        # The help_text may be updated via JavaScript
        help_text = "Enter the headline figure details."
        template = "templates/components/streamfield/headline_figures_item_block.html"


class HeadlineFiguresItemBlockAdapter(StructBlockAdapter):
    js_constructor = "cms.core.widgets.HeadlineFiguresItemBlock"

    @cached_property
    def media(self) -> forms.Media:
        parent_js = super().media._js  # pylint: disable=protected-access
        return forms.Media(js=[*parent_js, "js/blocks/headline-figures-item-block.js"])


register(HeadlineFiguresItemBlockAdapter(), HeadlineFiguresItemBlock)
