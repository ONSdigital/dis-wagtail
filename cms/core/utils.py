import io
import json
import re
import string
from itertools import chain
from threading import Lock
from typing import TYPE_CHECKING, Any

from django.conf import settings
from django.http import HttpResponsePermanentRedirect, HttpResponseRedirect
from django.shortcuts import redirect as _redirect

from cms.core.enums import RelatedContentType

if TYPE_CHECKING:
    from django.http import HttpRequest
    from wagtail.models import Page

matplotlib_lock = Lock()

# C0 and C1
CONTROL_CHARACTERS = frozenset(chr(z) for z in chain(range(32), range(0x7F, 0xA0)))

# Allow whitespace
UNWANTED_CONTROL_CHARACTERS = CONTROL_CHARACTERS - set(string.whitespace)

# Pre-encode control characters in pattern to replace without decoding
JSON_ENCODED_UNWANTED_CONTROL_CHARS_RE = re.compile(
    "|".join(re.escape(json.dumps(z).strip('"')) for z in UNWANTED_CONTROL_CHARACTERS)
)

# A set of tuples containing the beginning and end indicators for LaTeX formulas
FORMULA_INDICATORS: set[tuple[str, str]] = {("$$", "$$"), ("\\(", "\\)"), ("\\[", "\\]")}

MATPLOTLIB_CONTEXT = {
    # Use LaTeX to render text in matplotlib
    "text.usetex": True,
    # Load the amsmath package for LaTeX
    "text.latex.preamble": r"\usepackage{amsmath}",
}

if TYPE_CHECKING:
    from django.http import HttpRequest
    from django_stubs_ext import StrOrPromise


def get_content_type_for_page(page: Page) -> StrOrPromise:
    """Returns the content type for a given page."""
    label: StrOrPromise = page.specific_deferred.label
    return label


def get_related_content_type_label(content_type: str) -> str:
    """Returns the label for a given related content type."""
    label: str = getattr(RelatedContentType, content_type).label
    return label


def get_client_ip(request: HttpRequest) -> str | None:
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
    # Only import matplotlib when needed, as the import is large and rarely used
    import matplotlib as mpl  # pylint: disable=import-outside-toplevel
    from matplotlib.figure import Figure  # pylint: disable=import-outside-toplevel

    with matplotlib_lock, mpl.rc_context(MATPLOTLIB_CONTEXT):
        fig = Figure()

        with io.StringIO() as svg_buffer:
            fig.text(0, 0, rf"${latex}$", fontsize=fontsize)
            fig.savefig(svg_buffer, format="svg", bbox_inches="tight", transparent=transparent)
            svg_string = svg_buffer.getvalue()

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
    *, page: Page, request: HttpRequest, listing_url_method_name: str
) -> HttpResponseRedirect | HttpResponsePermanentRedirect:
    """Redirects to the parent page's listing URL if available, otherwise to the parent page itself."""
    if not (parent := getattr(page.get_parent(), "specific_deferred", None)):
        return redirect("/")

    method = getattr(parent, listing_url_method_name, None)
    if callable(method) and (redirect_url := method()):
        return redirect(redirect_url)
    return redirect(parent.get_url(request=request))


def strip_unwanted_control_chars_from_json(data: str) -> str:
    """Remove control characters (C0 and C1) from JSON string (without decoding)."""
    return JSON_ENCODED_UNWANTED_CONTROL_CHARS_RE.sub("", data)


def deep_merge_dicts(dict1: dict, dict2: dict) -> dict:
    """Deep merge dictionaries.
    If there are conflicting keys, dict2 takes precedence.
    """
    result = dict1.copy()

    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge_dicts(result[key], value)
        else:
            result[key] = value

    return result
