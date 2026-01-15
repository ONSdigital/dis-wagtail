import io
from threading import Lock
from typing import TYPE_CHECKING, Any

import matplotlib as mpl
from django.conf import settings
from django.http import HttpResponsePermanentRedirect, HttpResponseRedirect
from django.shortcuts import redirect as _redirect
from matplotlib.figure import Figure

from cms.core.enums import RelatedContentType

if TYPE_CHECKING:
    from django.http import HttpRequest
    from wagtail.models import Page

matplotlib_lock = Lock()

# A set of tuples containing the beginning and end indicators for LaTeX formulas
FORMULA_INDICATORS: set[tuple[str, str]] = {("$$", "$$"), ("\\(", "\\)"), ("\\[", "\\]")}

mpl.rcParams.update(
    {
        # Use LaTeX to render text in matplotlib
        "text.usetex": True,
        # Load the amsmath package for LaTeX
        "text.latex.preamble": r"\usepackage{amsmath}",
    }
)


if TYPE_CHECKING:
    from django.http import HttpRequest
    from django_stubs_ext import StrOrPromise


def get_content_type_for_page(page: "Page") -> "StrOrPromise":
    """Returns the content type for a given page."""
    label: StrOrPromise = page.specific_deferred.label
    return label


def get_related_content_type_label(content_type: str) -> str:
    """Returns the label for a given related content type."""
    label: str = getattr(RelatedContentType, content_type).label
    return label


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


def redirect(
    to: str, *args: Any, permanent: bool = False, preserve_request: bool = True, **kwargs: Any
) -> HttpResponseRedirect | HttpResponsePermanentRedirect:
    """Wrapper for Django's redirect that defaults preserve_request=True."""
    return _redirect(
        to,
        *args,
        permanent=permanent,
        preserve_request=preserve_request,
        **kwargs,
    )


def redirect_to_parent_listing(
    *, page: "Page", request: "HttpRequest", listing_url_method_name: str
) -> HttpResponseRedirect | HttpResponsePermanentRedirect:
    """Redirects to the parent page's listing URL if available, otherwise to the parent page itself."""
    if not (parent := getattr(page.get_parent(), "specific_deferred", None)):
        return redirect("/")

    method = getattr(parent, listing_url_method_name, None)
    if callable(method) and (redirect_url := method()):
        return redirect(redirect_url)
    return redirect(parent.get_url(request=request))


def flatten_table_data(data: dict) -> list[list[str | int | float]]:
    """Flattens table data by extracting cell values from headers and rows.

    This is primarily used for the table block. Merged cells (colspan/rowspan)
    have their values repeated across all spanned cells.

    Args:
        data: Dictionary containing 'headers' and 'rows' keys with cell objects.

    Returns:
        List of rows, where each row is a list of cell values (strings, ints, or floats).
    """
    all_rows = [*data.get("headers", []), *data.get("rows", [])]
    result: list[list[str | int | float]] = []
    # Track columns filled by rowspan: {col_index: (value, remaining_rows)}
    rowspan_tracker: dict[int, tuple[str | int | float, int]] = {}

    for row in all_rows:
        processed_row: list[str | int | float] = []
        col_index = 0

        for cell in row:
            # Fill columns blocked by previous rowspans
            while col_index in rowspan_tracker:
                value, remaining = rowspan_tracker[col_index]
                processed_row.append(value)
                if remaining == 1:
                    del rowspan_tracker[col_index]
                else:
                    rowspan_tracker[col_index] = (value, remaining - 1)
                col_index += 1

            value = cell.get("value", "")
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
        while col_index in rowspan_tracker:
            value, remaining = rowspan_tracker[col_index]
            processed_row.append(value)
            if remaining == 1:
                del rowspan_tracker[col_index]
            else:
                rowspan_tracker[col_index] = (value, remaining - 1)
            col_index += 1

        result.append(processed_row)

    return result
