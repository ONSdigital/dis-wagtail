from typing import TYPE_CHECKING

from django import forms
from django.utils.functional import cached_property
from wagtail.blocks import CharBlock, PageChooserBlock, StreamBlock, StructBlock, URLBlock
from wagtail.blocks.struct_block import StructBlockAdapter
from wagtail.images.blocks import ImageChooserBlock
from wagtail.telepath import register

from .viewsets import series_with_headline_figures_chooser_viewset

if TYPE_CHECKING:
    from wagtail.blocks import ChooserBlock, StreamValue, StructValue
    from wagtail.models import Page

    from cms.articles.models import ArticleSeriesPage, StatisticalArticlePage


class ExploreMoreExternalLinkBlock(StructBlock):
    url = URLBlock(label="External URL")
    title = CharBlock()
    description = CharBlock()
    thumbnail = ImageChooserBlock()

    class Meta:
        icon = "link"

    def get_formatted_value(self, value: "StructValue", context: dict | None = None) -> dict[str, str | dict]:  # pylint: disable=unused-argument
        """Returns the value formatted for the Design System onsDocumentList macro."""
        renditions = value["thumbnail"].get_renditions("fill-144x100", "fill-288x200")
        return {
            "thumbnail": {
                "smallSrc": renditions["fill-144x100"].url,
                "largeSrc": renditions["fill-288x200"].url,
            },
            "title": {
                "text": value["title"],
                "url": value["url"],
            },
            "description": value["description"],
        }


class ExploreMoreInternalLinkBlock(StructBlock):
    page = PageChooserBlock()
    title = CharBlock(required=False, help_text="Use to override the chosen page title.")
    description = CharBlock(
        required=False,
        help_text=(
            "Use to override the chosen page description. "
            "By default, we will attempt to use the listing summary or the summary field."
        ),
    )
    thumbnail = ImageChooserBlock(required=False, help_text="Use to override the chosen page listing image.")

    class Meta:
        icon = "doc-empty-inverse"

    def get_formatted_value(self, value: "StructValue", context: dict | None = None) -> dict[str, str | dict]:
        """Returns the value formatted for the Design System onsDocumentList macro."""
        page: Page = value["page"].specific_deferred
        if not page.live:
            return {}

        formatted_value = {
            "title": {
                "text": value["title"] or getattr(page, "display_title", page.title),
                "url": page.get_url(request=context.get("request") if context else None),
            },
            "description": value["description"] or getattr(page, "listing_summary", "") or getattr(page, "summary", ""),
        }
        if image := (value["thumbnail"] or getattr(page, "listing_image", None)):
            renditions = image.get_renditions("fill-144x100", "fill-288x200")
            formatted_value["thumbnail"] = {
                "smallSrc": renditions["fill-144x100"].url,
                "largeSrc": renditions["fill-288x200"].url,
            }
        return formatted_value


class ExploreMoreStoryBlock(StreamBlock):
    external_link = ExploreMoreExternalLinkBlock()
    internal_link = ExploreMoreInternalLinkBlock()

    class Meta:
        template = "templates/components/streamfield/explore_more_stream_block.html"

    def get_context(self, value: "StreamValue", parent_context: dict | None = None) -> dict:
        context: dict = super().get_context(value, parent_context=parent_context)

        formatted_items = []
        for child in value:
            if formatted_item := child.block.get_formatted_value(child.value, context=context):
                formatted_items.append(formatted_item)

        context["formatted_items"] = formatted_items
        return context


SeriesChooserBlock: "ChooserBlock" = series_with_headline_figures_chooser_viewset.get_block_class(
    name="SeriesChooserBlock", module_path="cms.topics.blocks"
)


class LinkedSeriesChooserBlock(SeriesChooserBlock):
    def __init__(self, required=True, help_text=None, validators=(), **kwargs):
        super().__init__(required=required, help_text=help_text, validators=validators, **kwargs)
        self.widget = series_with_headline_figures_chooser_viewset.widget_class(
            linked_fields={"topic_page_id": "#id_topic_page_id"}
        )


class TopicHeadlineFigureBlock(StructBlock):
    series = LinkedSeriesChooserBlock()
    figure = CharBlock()


class TopicHeadlineFiguresStreamBlock(StreamBlock):
    figures = TopicHeadlineFigureBlock()

    def get_context(self, value: "StreamValue", parent_context: dict | None = None) -> dict:
        context: dict = super().get_context(value, parent_context=parent_context)

        figure_data = []
        for item in value:
            series: ArticleSeriesPage = item.value["series"]
            latest_article: StatisticalArticlePage = series.get_latest()

            if figure := latest_article.get_headline_figure(item.value["figure"]):
                figure["url"] = latest_article.get_url(request=context.get("request"))
                figure_data.append(figure)

        context["figure_data"] = figure_data
        return context

    class Meta:
        icon = "pick"
        label = "Headline figures"
        template = "templates/components/streamfield/topic_headline_figures_block.html"


class SeriesWithHeadlineChooserAdapter(StructBlockAdapter):
    js_constructor = "cms.topics.widgets.TopicHeadlineFigureBlock"

    @cached_property
    def media(self):
        parent_js = super().media._js  # pylint: disable=protected-access
        return forms.Media(js=[*parent_js, "topics/js/headline-figure-block.js"])


register(SeriesWithHeadlineChooserAdapter(), TopicHeadlineFigureBlock)
