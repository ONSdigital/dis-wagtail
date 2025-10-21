import io
from threading import Lock
from typing import TYPE_CHECKING, Any

import matplotlib as mpl
from django.conf import settings
from django.http import HttpResponsePermanentRedirect, HttpResponseRedirect
from matplotlib.figure import Figure

from cms.core.enums import RelatedContentType

if TYPE_CHECKING:
    from django.http import HttpRequest
    from wagtail.models import Page


matplotlib_lock = Lock()

FORMULA_INDICATOR = "$$"

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
    """Returns an HttpResponseRedirect or HttpResponsePermanentRedirect to the specified URL.

    Args:
        to (str): The URL to redirect to.
        *args (Any): Additional positional arguments for the response.
        permanent (bool, optional): If True, returns a permanent redirect (status 308 or 301). Defaults to False.
        preserve_request (bool, optional): If True, preserves the request method (status 307 or 308). Defaults to True.
        **kwargs (Any): Additional keyword arguments for the response.

    Returns:
        HttpResponseRedirect or HttpResponsePermanentRedirect: The redirect response with the appropriate status code.
    """
    status = 308 if permanent and preserve_request else 307 if preserve_request else 301 if permanent else 302
    response_class = HttpResponsePermanentRedirect if permanent else HttpResponseRedirect
    response = response_class(to, *args, **kwargs)
    response.status_code = status
    return response


def redirect_to_parent_listing(
    page: "Page", request: "HttpRequest", listing_url_method_name: str
) -> HttpResponseRedirect | HttpResponsePermanentRedirect:
    """Redirects to the parent page's listing URL if available, otherwise to the parent page itself."""
    parent = getattr(page.get_parent(), "specific_deferred", None)
    method = getattr(parent, listing_url_method_name, None)

    if not parent:
        return redirect("/")

    if callable(method) and (redirect_url := method()):
        return redirect(redirect_url)
    return redirect(parent.get_url(request=request))
