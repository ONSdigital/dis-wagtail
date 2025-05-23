from typing import TYPE_CHECKING, Literal, Optional, TypedDict, cast

import jinja2
from django.http import HttpRequest
from django.utils.translation import gettext_lazy as _

if TYPE_CHECKING:
    from wagtail.blocks import StructValue
    from wagtail.models import Page

    from cms.navigation.models import FooterMenu, MainMenu

BREACRUMBS_HOMEPAGE_DEPTH = 2


class NavigationItem(TypedDict, total=False):
    heading: str
    text: str
    url: str
    description: str
    groupItems: list["NavigationItem"]


class ColumnData(TypedDict):
    groups: list[NavigationItem]


class FooterColumnData(TypedDict):
    title: str
    itemsList: list[NavigationItem]


def _extract_item(
    value: "StructValue",
    text_key: Literal["text", "heading"],
    request: Optional["HttpRequest"] = None,
    include_description: bool = False,
) -> NavigationItem:
    """Extracts text/url from the StructValue.
    If include_description=True, also extracts the description field.
    """
    item: NavigationItem = {}

    if value["external_url"]:
        item[text_key] = value["title"]
        item["url"] = value["external_url"]

    elif value["page"] and value["page"].live:
        item[text_key] = value["title"] or value["page"].title
        item["url"] = value["page"].get_url(request=request)

    if include_description and "description" in value:
        item["description"] = value["description"]

    return item


@jinja2.pass_context
def main_menu_highlights(
    context: jinja2.runtime.Context, main_menu: Optional["MainMenu"] = None
) -> list[NavigationItem]:
    if not main_menu:
        return []

    highlights = []
    for highlight in main_menu.highlights:
        highlight_data = _extract_item(
            highlight.value, request=context.get("request"), include_description=True, text_key="heading"
        )
        if highlight_data:
            highlights.append(highlight_data)

    return highlights


@jinja2.pass_context
def main_menu_columns(context: jinja2.runtime.Context, main_menu: Optional["MainMenu"] = None) -> list[ColumnData]:
    if not main_menu:
        return []

    def extract_section_data(
        section: "StructValue", request: Optional["HttpRequest"] = None
    ) -> Optional[NavigationItem]:
        section_data = _extract_item(
            section["section_link"], request=request, include_description=False, text_key="heading"
        )
        if not section_data:
            return None

        children = []
        for link in section["links"]:
            link_data = _extract_item(link, request=request, include_description=False, text_key="text")
            if link_data:
                children.append(link_data)

        section_data["groupItems"] = children
        return section_data

    items: list[ColumnData] = []
    for column in main_menu.columns:
        column_data: ColumnData = {"groups": []}

        for section in column.value["sections"]:
            if section_data := extract_section_data(section, context.get("request")):
                column_data["groups"].append(section_data)

        if column_data["groups"]:
            items.append(column_data)

    return items


@jinja2.pass_context
def footer_menu_columns(
    context: jinja2.runtime.Context, footer_menu: Optional["FooterMenu"] = None
) -> list[FooterColumnData]:
    if not footer_menu:
        return []

    columns_data = []
    for column in footer_menu.columns:
        column_value = column.value
        column_title = column_value.get("title")

        links_list = []
        for link_struct in column_value.get("links", []):
            link_data = _extract_item(link_struct, request=context.get("request"), text_key="text")
            if link_data:
                links_list.append(link_data)

        columns_data.append(cast(FooterColumnData, {"title": column_title, "itemsList": links_list}))
    return columns_data


@jinja2.pass_context
def breadcrumbs(context: jinja2.runtime.Context, page: "Page", include_self: bool = False) -> list[dict[str, object]]:
    """Returns the breadcrumbs as a list of dictionaries for the given page."""
    breadcrumbs_list = []
    request = context.get("request")
    for ancestor_page in page.get_ancestors().specific().defer_streamfields():
        if ancestor_page.is_root():
            continue
        if ancestor_page.depth <= BREACRUMBS_HOMEPAGE_DEPTH:
            breadcrumbs_list.append({"url": "/", "text": _("Home")})
        elif not getattr(ancestor_page, "exclude_from_breadcrumbs", False):
            breadcrumbs_list.append({"url": ancestor_page.get_url(request=request), "text": ancestor_page.title})
    if include_self:
        breadcrumbs_list.append({"url": page.get_url(request=request), "text": page.title})
    return breadcrumbs_list
