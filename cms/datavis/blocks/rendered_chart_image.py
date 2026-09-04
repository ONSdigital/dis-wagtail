from __future__ import annotations

from typing import TYPE_CHECKING, Any

from django import forms
from wagtail.blocks import ChooserBlock

from cms.datavis.models import RenderedChartImage

if TYPE_CHECKING:
    from collections.abc import Mapping

    from django.core.files.uploadedfile import UploadedFile
    from django.utils.datastructures import MultiValueDict


class RenderedChartImageWidget(forms.HiddenInput):
    """Widget for the hidden rendered_chart_image chooser field.

    The field is populated only by the chart render pipeline and never edited directly by
    editors, so a plain hidden input is enough; there is no need for the full chooser modal UI.
    """

    def value_from_datadict(self, data: Mapping[str, Any], files: MultiValueDict[str, UploadedFile], name: str) -> Any:
        # Treat the empty string as "nothing chosen", as Wagtail's own chooser widgets do.
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
