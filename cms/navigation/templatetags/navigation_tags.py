from typing import TYPE_CHECKING, Optional, TypedDict

import jinja2
from django.http import HttpRequest

if TYPE_CHECKING:
    from wagtail.blocks import StructValue

    from cms.navigation.models import FooterMenu, MainMenu


class CommonItem(TypedDict, total=False):
    text: str
    url: str
    description: str
    children: list["CommonItem"]


class ColumnData(TypedDict):
    column: int
    linksList: list[CommonItem]


def _extract_item(
    value: "StructValue",
    request: Optional["HttpRequest"] = None,
    include_description: bool = False,
) -> CommonItem:
    """Extracts text/url from the StructValue.
    If include_description=True, also extracts the description field.
    """
    item: CommonItem = {}

    if value["external_url"]:
        item["text"] = value["title"]
        item["url"] = value["external_url"]

    elif value["page"] and value["page"].live:
        item["text"] = value["title"] or value["page"].title
        item["url"] = value["page"].get_url(request=request)

    if include_description and "description" in value:
        item["description"] = value["description"]

    return item


@jinja2.pass_context
def main_menu_highlights(context: jinja2.runtime.Context, main_menu: Optional["MainMenu"] = None) -> list[CommonItem]:
    if not main_menu:
        return []

    highlights = []
    for highlight in main_menu.highlights:
        highlight_data = _extract_item(highlight.value, request=context.get("request"), include_description=True)
        if highlight_data:
            highlights.append(highlight_data)

    return highlights


@jinja2.pass_context
def main_menu_columns(context: jinja2.runtime.Context, main_menu: Optional["MainMenu"] = None) -> list[ColumnData]:
    if not main_menu:
        return []

    def extract_section_data(section: "StructValue", request: Optional["HttpRequest"] = None) -> Optional[CommonItem]:
        section_data = _extract_item(section["section_link"], request=request, include_description=False)
        if not section_data:
            return None

        children = []
        for link in section["links"]:
            link_data = _extract_item(link, request=request, include_description=False)
            if link_data:
                children.append(link_data)

        section_data["children"] = children
        return section_data

    items: list[ColumnData] = []
    for idx, column in enumerate(main_menu.columns):
        column_data: ColumnData = {"column": idx, "linksList": []}

        for section in column.value["sections"]:
            if section_data := extract_section_data(section, context.get("request")):
                column_data["linksList"].append(section_data)

        if column_data["linksList"]:
            items.append(column_data)

    return items


class FooterColumnData(TypedDict):
    column: int
    title: str
    linksList: list[CommonItem]


@jinja2.pass_context
def footer_menu_columns(
    context: jinja2.runtime.Context, footer_menu: Optional["FooterMenu"] = None
) -> list[FooterColumnData]:
    if not footer_menu:
        print("footer_menu is None")
        return []

    items: list[FooterColumnData] = []
    for idx, column in enumerate(footer_menu.columns):
        column_data: FooterColumnData = {"column": idx, "title": column.value["title"], "linksList": []}
        print("")

        for link in column.value["links"]:
            link_data = _extract_item(link, request=context.get("request"), include_description=False)
            if link_data:
                column_data["linksList"].append(link_data)

        if column_data["linksList"]:
            items.append(column_data)

    return items
