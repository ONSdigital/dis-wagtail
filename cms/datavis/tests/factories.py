import json

from factory import Factory

from cms.datavis.blocks.table import TableDataType


class TableDataFactory(Factory):
    """Factory to create table data in the format expected by SimpleTableBlock."""

    class Meta:
        model = dict

    table_data: TableDataType

    @classmethod
    def _create(cls, model_class, *args, table_data: TableDataType | None = None, **kwargs) -> dict[str, str]:
        if table_data is None:
            table_data = [
                ["Header 1", "Header 2", "Header 3"],
                ["Row 1, Column 1", "Row 1, Column 2", "Row 1, Column 3"],
                ["Row 2, Column 1", "Row 2, Column 2", "Row 2, Column 3"],
            ]

        return {
            "table_data": json.dumps({"data": table_data}),
        }
