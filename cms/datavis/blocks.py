from copy import copy
from typing import TYPE_CHECKING, Any, Optional

from django.db.models import Prefetch
from django.forms.widgets import Media
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from wagtail import blocks
from wagtail.snippets.blocks import SnippetChooserBlock
from wagtail.telepath import register
from wagtailtables.blocks import TableAdapter, TableBlock

if TYPE_CHECKING:
    from django.db.models import QuerySet
    from django.http import HttpRequest
    from wagtail.blocks.struct_block import StructValue

    from cms.datavis.models import Visualisation


class SimpleTableBlock(TableBlock):
    table_data = blocks.TextBlock(label=_("Data"), default="[]")
    caption = None
    header_row = None
    header_col = None


class SimpleTableBlockAdapter(TableAdapter):
    def js_args(self, block: "SimpleTableBlock") -> list[Any]:
        result: list[Any] = super().js_args(block)
        # We override wagtailtables js to remove the toolbar, as formatting
        # options are irrelevant to our data-only tables.
        result[2].pop("toolbar", None)
        return result

    @cached_property
    def media(self) -> Media:
        # wagtailtables css doen't resize the widget container correctly, so we
        # need to add custom css to fix it.
        super_media: Media = super().media
        return super_media + Media(css={"all": ["wagtailtables/css/table-dataset.css"]})


register(SimpleTableBlockAdapter(), SimpleTableBlock)


class VisualisationChooserBlock(SnippetChooserBlock):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__("datavis.Visualisation", *args, **kwargs)

    def get_to_python_queryset(self) -> "QuerySet[Visualisation]":
        from cms.datavis.models import AdditionalDataSource, Visualisation  # pylint: disable=import-outside-toplevel

        return (  # type: ignore[no-any-return]
            Visualisation.objects.select_related("primary_data_source").prefetch_related(
                "annotations",
                Prefetch(
                    "additional_data_sources",
                    queryset=AdditionalDataSource.objects.all().select_related("data_source"),
                ),
            )
        )

    def to_python(self, value: int | None) -> Optional["Visualisation"]:
        # the incoming serialised value should be None or an ID
        if value is None:
            return value
        try:
            return self.get_to_python_queryset().get(pk=value).specific  # type: ignore[no-any-return]
        except self.model_class.DoesNotExist:
            return None

    def bulk_to_python(self, values: list[int]) -> list["Visualisation | None"]:
        objects = self.get_to_python_queryset().in_bulk(values)
        seen_ids = set()
        result = []

        for pk in values:
            obj = objects.get(pk)
            if obj is not None:
                obj = obj.specific
                if pk in seen_ids:
                    # this object is already in the result list, so we need to make a copy
                    obj = copy(obj)

            result.append(obj)
            seen_ids.add(pk)

        return result


class DataVisBlock(blocks.StructBlock):
    visualisation = VisualisationChooserBlock()
    title = blocks.CharBlock(label=_("Title"))
    subtitle = blocks.CharBlock(label=_("Subtitle"))

    class Meta:
        template = "templates/components/streamfield/datavis_block.html"

    def get_context(self, value: "StructValue", parent_context: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        context: dict[str, Any] = super().get_context(value, parent_context)
        request: Optional[HttpRequest] = parent_context.get("request") if parent_context else None
        visualisation: Visualisation = value["visualisation"].specific

        # Override the title and subtitle
        visualisation.title = value["title"]
        visualisation.subtitle = value["subtitle"]

        # Add template and visualisation context to support rendering
        context.update(visualisation.get_context(request))
        context["visualisation_template"] = visualisation.get_template()
        return context
