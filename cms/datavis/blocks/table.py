import json
from collections.abc import Sequence
from typing import Any

from django.forms.widgets import Media
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from wagtail import blocks
from wagtail.admin.telepath import register
from wagtail.blocks.struct_block import StructValue
from wagtailtables.blocks import TableAdapter, TableBlock

from cms.datavis.utils import numberfy

RowType = list[str | float | int]
TableDataType = Sequence[RowType]


class SimpleTableStructValue(StructValue):
    @cached_property
    def _data(self) -> TableDataType:
        """Cache the extracted and processed table data."""
        if not self.get("table_data"):
            return []
        # Decoding the json string value
        table_data: dict[str, TableDataType] = json.loads(self.get("table_data"))
        try:
            data: TableDataType = table_data["data"]
        except TypeError:
            # When the table is empty, the json is not a dict
            return []

        # Convert valid number strings to ints/floats
        if len(data) > 1:
            for row in data[1:]:
                for i, val in enumerate(row):
                    if isinstance(val, str):
                        row[i] = numberfy(val)
        return data

    @cached_property
    def headers(self) -> RowType:
        if not self._data:
            return []
        headers: RowType = self._data[0]
        return headers

    @cached_property
    def rows(self) -> TableDataType:
        if not self._data:
            return []
        rows: TableDataType = self._data[1:]
        return rows


class SimpleTableBlock(TableBlock):
    table_data = blocks.TextBlock(label=_("Data"), default="[]")
    caption = None
    header_row = None
    header_col = None

    class Meta:
        value_class = SimpleTableStructValue


class SimpleTableBlockAdapter(TableAdapter):
    def js_args(self, block: SimpleTableBlock) -> list[Any]:
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
