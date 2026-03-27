import csv
import re
from collections.abc import Mapping

from bs4 import BeautifulSoup, Tag
from django.http import HttpResponse
from django.utils.text import slugify


def clean_cell_value(value: str | int | float) -> str | int | float:
    """Cleans a cell value for CSV export.

    Args:
        value: The cell value to clean.

    Returns:
        The cleaned cell value as a string, int, or float.
    """
    if not isinstance(value, str):
        return value

    value = value.strip()

    # Replace <br> tags (all variations) with newlines
    value = re.sub(r"<br\s*/?>", "\n", value, flags=re.IGNORECASE)

    if "<" not in value:
        # Return early if there are no HTML tags to process
        return value

    # Strip all HTML tags except <a> tags (preserve links)
    soup = BeautifulSoup(value, "html.parser")
    for tag in soup.find_all(True):
        if isinstance(tag, Tag) and tag.name != "a":
            tag.unwrap()
    # Use formatter=None to avoid escaping < characters in text content
    return soup.decode(formatter=None)  # type: ignore[arg-type]


def flatten_table_data(data: Mapping) -> list[list[str | int | float]]:
    """Flattens table data by extracting cell values from headers and rows.

    This is primarily used for the table block. Merged cells (colspan/rowspan)
    have their values repeated across all spanned cells.

    Args:
        data: Data containing 'headers' and 'rows' keys with cell objects.

    Returns:
        List of rows, where each row is a list of cell values (strings, ints, or floats).
    """
    all_rows = [*data.get("headers", []), *data.get("rows", [])]
    result: list[list[str | int | float]] = []
    # Track columns filled by rowspan: {col_index: (value, remaining_rows)}
    rowspan_tracker: dict[int, tuple[str | int | float, int]] = {}

    # Use closure to access rowspan_tracker
    def fill_rowspan_columns(processed_row: list[str | int | float], col_index: int) -> int:
        """Fill columns blocked by previous rowspans, returning the updated column index."""
        while col_index in rowspan_tracker:
            value, remaining = rowspan_tracker[col_index]
            processed_row.append(value)
            if remaining == 1:
                del rowspan_tracker[col_index]
            else:
                rowspan_tracker[col_index] = (value, remaining - 1)
            col_index += 1
        return col_index

    for row in all_rows:
        processed_row: list[str | int | float] = []
        col_index = 0

        for cell in row:
            # Fill columns blocked by previous rowspans
            col_index = fill_rowspan_columns(processed_row, col_index)

            value = clean_cell_value(cell.get("value", ""))
            colspan = cell.get("colspan", 1)
            rowspan = cell.get("rowspan", 1)

            # Add the cell value repeated for colspan
            for _ in range(colspan):
                processed_row.append(value)
                # Track rowspan for this column
                if rowspan > 1:
                    rowspan_tracker[col_index] = (value, rowspan - 1)
                col_index += 1

        # Handle any remaining rowspan columns at end of row
        fill_rowspan_columns(processed_row, col_index)  # Return value not needed

        result.append(processed_row)

    return result


def sanitize_data_for_csv(data: list[list[str | int | float]]) -> list[list[str | int | float]]:
    """Sanitize data for CSV export by escaping formula triggers.

    Prevents CSV injection by prepending ' to strings starting with
    =, +, -, @, or tab characters.
    """
    triggers = ("=", "+", "-", "@", "\t")

    return [
        [f"'{value}" if isinstance(value, str) and value.startswith(triggers) else value for value in row]
        for row in data
    ]


def create_data_csv_download_response_from_data(data: list[list[str | int | float]], *, title: str) -> HttpResponse:
    """Creates a Django HttpResponse for downloading a CSV file from table data.

    Args:
        data: The list of data rows to be converted to CSV, where each row is a list of values.
        title: The title for the CSV file, which will be slugified to create the filename.

    Returns:
        A Django HttpResponse object configured for CSV file download.
    """
    filename = slugify(title) or "chart"
    response = HttpResponse(
        content_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}.csv"',
        },
    )
    writer = csv.writer(response)
    writer.writerows(sanitize_data_for_csv(data))
    return response
