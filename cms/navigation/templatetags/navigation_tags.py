from typing import TYPE_CHECKING, Literal, TypedDict, cast

import jinja2
from django.http import HttpRequest

if TYPE_CHECKING:
    from wagtail.blocks import StructValue

    from cms.navigation.models import FooterMenu, MainMenu

BREACRUMBS_HOMEPAGE_DEPTH = 2


class NavigationItem(TypedDict, total=False):
    heading: str
    text: str
    url: str
    description: str
    groupItems: list[NavigationItem]
    attributes: dict[str, str]


class ColumnData(TypedDict):
    groups: list[NavigationItem]


class FooterColumnData(TypedDict):
    title: str
    itemsList: list[NavigationItem]


def _extract_item(
    value: StructValue,
    text_key: Literal["text", "heading"],
    navigation_type: str,
    request: HttpRequest | None = None,
    include_description: bool = False,
) -> NavigationItem:
    """Extracts text/url from the StructValue.
    If include_description=True, also extracts the description field.
    """
    item: NavigationItem = {
        "attributes": {
            "data-ga-event": "navigation-click",
            "data-ga-navigation-type": navigation_type,
        }
    }

    if value["external_url"]:
        item[text_key] = value["title"]
        item["url"] = value["external_url"]

        item["attributes"]["data-ga-link-text"] = value["title"]

    elif (page := value.get("page")) and page.live:
        item[text_key] = value["title"] or getattr(page.specific_deferred, "display_title", page.title)

        item["url"] = page.specific_deferred.get_relative_path(request=request)

        item["attributes"]["data-ga-link-text"] = item[text_key]
        item["attributes"]["data-ga-click-path"] = item["url"]
        if content_type := page.specific_deferred.cached_analytics_values.get("contentType"):
            item["attributes"]["data-ga-click-content-type"] = content_type
        if content_group := page.specific_deferred.cached_analytics_values.get("contentGroup"):
            item["attributes"]["data-ga-click-content-group"] = content_group

    if include_description and "description" in value:
        item["description"] = value["description"]

    return item


@jinja2.pass_context
def main_menu_highlights(context: jinja2.runtime.Context, main_menu: MainMenu | None = None) -> list[NavigationItem]:
    if not main_menu:
        return []

    highlights = []
    for highlight in main_menu.highlights:
        highlight_data = _extract_item(
            highlight.value,
            text_key="heading",
            navigation_type="top-navigation",
            request=context.get("request"),
            include_description=True,
        )
        if highlight_data:
            highlights.append(highlight_data)

    return highlights


@jinja2.pass_context
def main_menu_columns(context: jinja2.runtime.Context, main_menu: MainMenu | None = None) -> list[ColumnData]:
    if not main_menu:
        return []

    def extract_section_data(section: StructValue, request: HttpRequest | None = None) -> NavigationItem | None:
        section_data = _extract_item(
            section["section_link"],
            text_key="heading",
            navigation_type="top-navigation",
            request=request,
            include_description=False,
        )
        if not section_data:
            return None

        children = []
        for link in section["links"]:
            link_data = _extract_item(
                link, text_key="text", navigation_type="top-navigation", request=request, include_description=False
            )
            if link_data:
                children.append(link_data)

        section_data["groupItems"] = children
        return section_data

    items: list[ColumnData] = []
    for column in main_menu.columns:
        groups: list[NavigationItem] = []

        for section in column.value["sections"]:
            if section_data := extract_section_data(section, context.get("request")):
                groups.append(section_data)

        if groups:
            items.append({"groups": groups})

    return items


@jinja2.pass_context
def footer_menu_columns(
    context: jinja2.runtime.Context, footer_menu: FooterMenu | None = None
) -> list[FooterColumnData]:
    if not footer_menu:
        return []

    columns_data = []
    for column in footer_menu.columns:
        column_value = column.value
        column_title = column_value.get("title")

        links_list = []
        for link_struct in column_value.get("links", []):
            link_data = _extract_item(
                link_struct, text_key="text", navigation_type="footer-navigation", request=context.get("request")
            )
            if link_data:
                links_list.append(link_data)

        columns_data.append(cast(FooterColumnData, {"title": column_title, "itemsList": links_list}))
    return columns_data
