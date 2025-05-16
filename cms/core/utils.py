import io
from threading import Lock
from typing import TYPE_CHECKING, Any, Optional, TypedDict

import matplotlib as mpl
from django.conf import settings
from django.db.models import QuerySet
from django.utils.formats import date_format
from django.utils.translation import gettext_lazy as _
from matplotlib.figure import Figure

matplotlib_lock = Lock()

FORMULA_INDICATOR = "$$"

# Use LaTeX to render text in matplotlib
mpl.rcParams.update({"text.usetex": True})

if TYPE_CHECKING:
    from django.http import HttpRequest
    from wagtail.models import Page


class DocumentListItem(TypedDict):
    title: dict[str, str]
    metadata: dict[str, Any]
    description: str


def get_formatted_pages_list(
    pages: list["Page"] | QuerySet["Page"], request: Optional["HttpRequest"] = None
) -> list[DocumentListItem]:
    """Returns a formatted list of page data for the documentList DS macro.

    See the search results section in https://service-manual.ons.gov.uk/design-system/components/document-list.
    """
    data = []
    for page in pages:
        datum: DocumentListItem = {
            "title": {
                "text": getattr(page, "display_title", page.title),
                "url": page.get_url(request=request),
            },
            "metadata": {
                "object": {"text": getattr(page, "label", _("Page"))},
            },
            "description": getattr(page, "listing_summary", "") or getattr(page, "summary", ""),
        }
        if release_date := page.release_date:
            datum["metadata"]["date"] = {
                "prefix": _("Released"),
                "showPrefix": True,
                "iso": date_format(release_date, "c"),
                "short": date_format(release_date, "DATE_FORMAT"),
            }
        data.append(datum)
    return data


def get_client_ip(request: "HttpRequest") -> str | None:
    """Get the IP address of the client.

    It's assumed this has been overridden by `django-xff`
    """
    if settings.IS_EXTERNAL_ENV:
        raise RuntimeError("Cannot get client IP in external environment.")
    return request.META.get("REMOTE_ADDR")


def latex_formula_to_svg(latex: str, *, fontsize: int = 18, transparent: bool = True) -> str:
    """Generates an SVG string from a LaTeX expression.

    Args:
        latex (str): The LaTeX string to render.
        fontsize (int, optional): The font size for the LaTeX output. Defaults to 18.
        transparent (bool, optional): If True, the SVG will have a transparent background. Defaults to True.

    Returns:
        str: A string containing the SVG representation of the LaTeX expression.
    """
    with matplotlib_lock:
        fig = Figure()
        svg_buffer = io.StringIO()
        try:
            fig.text(0, 0, rf"${latex}$", fontsize=fontsize)
            fig.savefig(svg_buffer, format="svg", bbox_inches="tight", transparent=transparent)
            svg_string = svg_buffer.getvalue()
        finally:
            svg_buffer.close()

        # Remove first 3 lines of the SVG string
        svg_string = "\n".join(svg_string.split("\n")[3:])

    return svg_string
