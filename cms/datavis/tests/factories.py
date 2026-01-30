import json

from factory import Factory

from cms.datavis.blocks.table import TableDataType


def make_table_block_value(
    *,
    title: str = "Test Table",
    caption: str = "",
    source: str = "",
    headers: list[list[str]] | None = None,
    rows: list[list[str]] | None = None,
) -> dict:
    """Generate a table block value structure for tests.

    Args:
        title: The table title.
        caption: Optional table caption.
        source: Optional table source.
        headers: List of header rows, each row is a list of header values.
                 Defaults to [["Header 1", "Header 2"]].
        rows: List of data rows, each row is a list of cell values.
              Defaults to [["Row 1 Col 1", "Row 1 Col 2"]].

    Returns:
        A dict matching the TableBlock value structure.
    """
    if headers is None:
        headers = [["Header 1", "Header 2"]]
    if rows is None:
        rows = [["Row 1 Col 1", "Row 1 Col 2"]]

    header_data = [[{"value": cell, "type": "th"} for cell in row] for row in headers]
    row_data = [[{"value": cell, "type": "td"} for cell in row] for row in rows]

    result: dict = {
        "title": title,
        "data": {
            "headers": header_data,
            "rows": row_data,
        },
    }
    if caption:
        result["caption"] = caption
    if source:
        result["source"] = source

    return result


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
