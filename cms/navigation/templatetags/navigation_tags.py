from typing import TYPE_CHECKING, Optional

import jinja2
from django import template
from django.http import HttpRequest

if TYPE_CHECKING:
    from wagtail.blocks import StructValue

    from cms.navigation.models import MainMenu


register = template.Library()


@jinja2.pass_context
def main_menu_highlights(
    context: jinja2.runtime.Context, main_menu: Optional["MainMenu"] = None
) -> list[dict[str, str]]:
    if not main_menu:
        return []

    highlights = []
    for highlight in main_menu.highlights:
        if highlight.value["external_url"]:
            highlights.append(
                {
                    "text": highlight.value["title"],
                    "description": highlight.value["description"],
                    "url": highlight.value["external_url"],
                }
            )
        elif highlight.value["page"] and highlight.value["page"].live:
            highlights.append(
                {
                    "text": highlight.value["title"] or highlight.value["page"].title,
                    "description": highlight.value["description"],
                    "url": highlight.value["page"].get_url(request=context.get("request")),
                }
            )

    return highlights


def _extract_url_item(value: "StructValue", request: Optional["HttpRequest"] = None) -> dict[str, str]:
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
    if not main_menu:
        return []

    items = []
    for idx, column in enumerate(main_menu.columns):
        column_data = {"column": idx, "linksList": []}

        for section in column.value["sections"]:
            section_data = _extract_url_item(section["section_link"], request=context.get("request"))
            if not section_data:
                continue

            section_data["children"] = []

            for link in section["links"]:
                if link_data := _extract_url_item(link, request=context.get("request")):
                    section_data["children"].append(link_data)

            column_data["linksList"].append(section_data)

        if column_data["linksList"]:
            items.append(column_data)

    return items
