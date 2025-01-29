from typing import TYPE_CHECKING, Optional, TypedDict

import jinja2
from django.http import HttpRequest

if TYPE_CHECKING:
    from wagtail.blocks import StructValue

    from cms.navigation.models import MainMenu


class LinkItem(TypedDict, total=False):
    text: str
    url: str
    children: list["LinkItem"]


class ColumnData(TypedDict):
    column: int
    linksList: list["LinkItem"]


def _extract_highlight_item(value: "StructValue", request: Optional["HttpRequest"] = None) -> dict[str, str]:
    if value["external_url"]:
        return {
            "text": value["title"],
            "description": value["description"],
            "url": value["external_url"],
        }

    if value["page"] and value["page"].live:
        return {
            "text": value["title"] or value["page"].title,
            "description": value["description"],
            "url": value["page"].get_url(request=request),
        }
    return {}


@jinja2.pass_context
def main_menu_highlights(
    context: jinja2.runtime.Context, main_menu: Optional["MainMenu"] = None
) -> list[dict[str, str]]:
    if not main_menu:
        return []

    highlights = []
    for highlight in main_menu.highlights:
        highlight_data = _extract_highlight_item(highlight.value, request=context.get("request"))
        if highlight_data:
            highlights.append(highlight_data)

    return highlights


def _extract_url_item(value: "StructValue", request: Optional["HttpRequest"] = None) -> LinkItem:
    if value["external_url"]:
        return {
            "text": value["title"],
            "url": value["external_url"],
        }

    if value["page"] and value["page"].live:
        return {
            "text": value["title"] or value["page"].title,
            "url": value["page"].get_url(request=request),
        }
    return {}


@jinja2.pass_context
def main_menu_columns(context: jinja2.runtime.Context, main_menu: Optional["MainMenu"] = None) -> list:
    items: list[ColumnData] = []

    if not main_menu:
        return []

    def extract_section_data(section: "StructValue", request: Optional["HttpRequest"] = None) -> Optional[LinkItem]:
        section_data = _extract_url_item(section["section_link"], request=request)
        if not section_data:
            return None

        section_data["children"] = [
            link_data for link in section["links"] if (link_data := _extract_url_item(link, request=request))
        ]

        return section_data

    items = []
    for idx, column in enumerate(main_menu.columns):
        column_data: ColumnData = {"column": idx, "linksList": []}

        for section in column.value["sections"]:
            if section_data := extract_section_data(section, context.get("request")):
                column_data["linksList"].append(section_data)

        if column_data["linksList"]:
            items.append(column_data)

    return items
