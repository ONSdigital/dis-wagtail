from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING, Any, ClassVar

from django import forms
from django.utils.functional import cached_property
from wagtail.blocks import CharBlock, PageChooserBlock, StreamBlock, StructBlock, URLBlock
from wagtail.blocks.struct_block import StructBlockAdapter
from wagtail.images.blocks import ImageChooserBlock
from wagtail.telepath import register

from cms.articles.models import ArticleSeriesPage

from .viewsets import series_with_headline_figures_chooser_viewset

if TYPE_CHECKING:
    from wagtail.blocks import ChooserBlock, StreamValue, StructValue
    from wagtail.models import Page

    from cms.articles.models import StatisticalArticlePage


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


class LinkedSeriesChooserWidget(series_with_headline_figures_chooser_viewset.widget_class):  # type:ignore[name-defined]
    target_model = ArticleSeriesPage
    linked_fields: ClassVar[dict] = {"topic_page_id": "#id_topic_page_id"}

    def get_value_data(self, value: Any) -> dict[str, Any]:
        data: dict[str, Any] = super().get_value_data(value)
        if data and value:
            instance = self.target_model.objects.get(pk=value)
            latest_article = instance.get_latest()
            if latest_article and latest_article.headline_figures.raw_data:
                # Return all headline figures available in these series
                data["figures"] = [dict(figure.value) for figure in latest_article.headline_figures]
        return data


class LinkedSeriesChooserBlock(SeriesChooserBlock):
    def __init__(
        self,
        required: bool = True,
        help_text: str | None = None,
        validators: Sequence[Callable[[Any], None]] = (),
        **kwargs: Any,
    ) -> None:
        super().__init__(required=required, help_text=help_text, validators=validators, **kwargs)
        self.widget = LinkedSeriesChooserWidget()


class TopicHeadlineFigureBlock(StructBlock):
    series = LinkedSeriesChooserBlock()
    figure_id = CharBlock()

    def get_context(self, value: "StructValue", parent_context: dict | None = None) -> dict:
        context: dict = super().get_context(value, parent_context=parent_context)

        if series_page := value["series"]:
            latest_article: StatisticalArticlePage | None = series_page.get_latest()

            if latest_article and (figure := latest_article.get_headline_figure(value["figure_id"])):
                figure["url"] = latest_article.get_url(request=context.get("request"))
                context["figure"] = figure

        return context

    class Meta:
        icon = "pick"
        label = "Headline figure"
        template = "templates/components/streamfield/topic_headline_figure_block.html"


class SeriesWithHeadlineChooserAdapter(StructBlockAdapter):
    js_constructor = "cms.topics.widgets.TopicHeadlineFigureBlock"

    @cached_property
    def media(self) -> forms.Media:
        parent_js = super().media._js  # pylint: disable=protected-access
        return forms.Media(js=[*parent_js, "topics/js/headline-figure-block.js"])


register(SeriesWithHeadlineChooserAdapter(), TopicHeadlineFigureBlock)
