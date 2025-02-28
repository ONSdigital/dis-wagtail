from typing import TYPE_CHECKING

from bs4 import BeautifulSoup

if TYPE_CHECKING:
    from bs4.element import PageElement


def html_table_to_dict(content: str) -> dict:
    """Take an HTML table and convert it to a dictionary.

    The dictionary has the following structure:
    - headers - a list of header row lists, each containing the cell info
    - rows - a list of row lists, each containing the cell info
    - html - the original html
    """
    # TODO: run content through nh3

    def get_cell_data(cell: "PageElement") -> dict[str, str | int]:
        cell_data = {"value": cell.text.strip(), "type": cell.name}

        if (rowspan := int(cell.get("rowspan", 1))) > 1:
            cell_data["rowspan"] = rowspan
        if (colspan := int(cell.get("colspan", 1))) > 1:
            cell_data["colspan"] = colspan
        if scope := cell.get("scope"):
            cell_data["scope"] = scope
        if align := cell.get("align"):
            cell_data["align"] = align

        return cell_data

    soup = BeautifulSoup(content, "html.parser")

    table = soup.find("table")
    if not table:
        return {
            "headers": [],
            "rows": [],
            "html": "",
        }

    # Extract headers
    headers = []
    if thead := table.find("thead"):
        headers.append([get_cell_data(header) for header in thead.find_all("th")])

        if tbody_rows := table.find("tbody"):
            table_rows = tbody_rows.find_all("tr")
        else:
            # If there's a thead but no tbody, get all rows not in thead
            table_rows = [row for row in table.find_all("tr") if row.parent != thead]
    else:
        table_rows = table.find_all("tr")
        # TODO: extract headers from tr if all cells are th?

    # Extract row data and convert to list of dictionaries
    rows = []
    for row in table_rows:
        rows.append([get_cell_data(cell) for cell in row.find_all(["td", "th"])])

    data = {
        "headers": headers,
        "rows": rows,
        "html": content,
    }

    return data
