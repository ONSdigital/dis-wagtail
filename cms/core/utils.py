import io
import json
import re
import string
from collections.abc import Callable, Mapping
from itertools import chain
from threading import Lock
from typing import TYPE_CHECKING, Any

from django.conf import settings
from django.http import HttpResponsePermanentRedirect, HttpResponseRedirect
from django.shortcuts import redirect as _redirect
from wagtail import hooks

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
    from django.http import HttpRequest, HttpResponse
    from django_stubs_ext import StrOrPromise


def get_content_type_for_page(page: Page) -> StrOrPromise | None:
    """Returns the content type for a given page."""
    label: StrOrPromise | None = page.specific_deferred.label
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

    # Type ignore: Matplotlib's stub expects rcParam keys as specific Literals; our shared dict is valid at runtime.
    with matplotlib_lock, mpl.rc_context(MATPLOTLIB_CONTEXT):  # type: ignore[arg-type]
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
    """Wrapper for Django's redirect that defaults preserve_request=True.

    User-provided redirect targets must be validated before calling this helper.
    """
    return _redirect(
        # codeql[py/url-redirection] This intentionally preserves Django's redirect helper contract.
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


def serve_page_with_view_restrictions(
    page: Page,
    request: HttpRequest,
    *,
    serve_callable: Callable[..., HttpResponse] | None = None,
    args: tuple[Any, ...] = (),
    kwargs: dict[str, Any] | None = None,
) -> HttpResponse:
    """Serve the given page (or a bound view method of it) through Wagtail's
    "on_serve_page" hook chain so the page's own view restrictions are enforced.

    Wagtail only checks view restrictions for the page matched by URL routing. When a
    routable page serves the content of a different page (e.g. ArticleSeriesPage serving
    StatisticalArticlePage editions), the rendered page's restrictions are never checked
    unless it is served through the hook chain, mirroring wagtail.views.serve.
    """

    def _serve(inner_page: Page, inner_request: HttpRequest, serve_args: Any, serve_kwargs: Any) -> HttpResponse:
        target = serve_callable if serve_callable is not None else inner_page.serve
        response: HttpResponse = target(inner_request, *serve_args, **serve_kwargs)
        return response

    serve_chain: Callable[..., HttpResponse] = _serve
    for fn in reversed(hooks.get_hooks("on_serve_page")):
        serve_chain = fn(serve_chain)
    return serve_chain(page, request, args, kwargs or {})


def strip_unwanted_control_chars_from_json(data: str) -> str:
    """Remove control characters (C0 and C1) from JSON string (without decoding)."""
    return JSON_ENCODED_UNWANTED_CONTROL_CHARS_RE.sub("", data)


def deep_merge_mapping(dict1: Mapping, dict2: Mapping) -> dict:
    """Deep merge mapping keys.
    Non-mapping values are referenced in the new dict, rather than copied.
    If there are conflicting keys, dict2 takes precedence.
    """
    # Must be a dict to allow internal mutation
    result = dict(dict1)

    for key, value in dict2.items():
        if key in result and isinstance(result[key], Mapping) and isinstance(value, Mapping):
            result[key] = deep_merge_mapping(result[key], value)
        else:
            result[key] = value

    return result
