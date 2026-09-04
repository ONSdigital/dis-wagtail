from typing import Any

from django import forms
from wagtail.blocks import ChooserBlock

from cms.datavis.models import RenderedChartImage


class RenderedChartImageWidget(forms.HiddenInput):
    """Widget for the hidden rendered_chart_image chooser field.

    The field is populated only by the chart render pipeline and never edited directly by
    editors, so a plain hidden input is enough; there is no need for the full chooser modal UI.
    """

    def value_from_datadict(self, data: dict, files: dict, name: str) -> Any:
        return super().value_from_datadict(data, files, name) or None

    def get_value_data(self, value: RenderedChartImage | int | None) -> int | None:
        if isinstance(value, RenderedChartImage):
            return value.pk
        return value


class RenderedChartImageChooserBlock(ChooserBlock):
    target_model = RenderedChartImage
    widget = RenderedChartImageWidget()

    class Meta:
        icon = "image"
