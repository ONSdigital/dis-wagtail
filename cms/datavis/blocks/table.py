import json
from collections.abc import Sequence
from typing import Any

from django.forms.widgets import Media
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from wagtail import blocks
from wagtail.blocks.struct_block import StructValue
from wagtail.telepath import register
from wagtailtables.blocks import TableAdapter, TableBlock

from cms.datavis.utils import numberfy


class SimpleTableStructValue(StructValue):
    @cached_property
    def _data(self) -> Sequence[Sequence[str | int | float]]:
        """Cache the extracted and processed table data."""
        if not self.get("table_data"):
            return []
        # Decoding the json string value
        data: list[list[str | float | int]] = json.loads(self.get("table_data"))["data"]

        # Convert valid number strings to ints/floats
        if len(data) > 1:
            for row in data[1:]:
                for i, val in enumerate(row):
                    if isinstance(val, str):
                        row[i] = numberfy(val)
        return data

    @cached_property
    def headers(self) -> Sequence[str | int | float]:
        if not self._data:
            return []
        headers: Sequence[str | int | float] = self._data[0]
        return headers

    @cached_property
    def rows(self) -> Sequence[Sequence[str | int | float]]:
        if not self._data:
            return []
        rows: Sequence[Sequence[str | int | float]] = self._data[1:]
        return rows


class SimpleTableBlock(TableBlock):
    table_data = blocks.TextBlock(label=_("Data"), default="[]")
    caption = None
    header_row = None
    header_col = None

    class Meta:
        value_class = SimpleTableStructValue


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
