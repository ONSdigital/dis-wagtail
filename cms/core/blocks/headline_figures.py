from typing import Any

from django.utils.translation import gettext as _
from wagtail.blocks import CharBlock, ListBlock, StructBlock


class HeadlineFiguresItemBlock(StructBlock):
    """Represents a headline figure."""

    title = CharBlock(label=_("Title"), max_length=60, required=True)
    figure = CharBlock(label=_("Figure"), max_length=10, required=True)
    supporting_text = CharBlock(label=_("Supporting text"), max_length=100, required=True)


class HeadlineFiguresBlock(ListBlock):
    """A list of headline figures."""

    def __init__(self, search_index: bool = True, **kwargs: Any) -> None:
        kwargs.setdefault("max_num", 4)
        super().__init__(HeadlineFiguresItemBlock, search_index=search_index, **kwargs)

    class Meta:
        icon = "data-analysis"
        label = _("Headline figures")
        template = "templates/components/streamfield/headline_figures_block.html"
