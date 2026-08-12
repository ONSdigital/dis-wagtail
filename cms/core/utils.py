import io
import json
import re
import string
from collections.abc import Callable, Generator, Mapping
from functools import wraps
from itertools import chain
from threading import Lock
from typing import TYPE_CHECKING, Any, overload

from django.conf import settings
from django.db import connections
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


class GeneratorCollector[T, R]:
    """Wrap a generator in a convenient API to access both the yielded and returned values."""

    value: R | None

    def __init__(self, gen: Generator[T, None, R]) -> None:
        self.gen = gen
        self.value = None

    def __iter__(self) -> Generator[T, None, R]:
        self.value = yield from self.gen
        return self.value

    def consume(self) -> None:
        for _ in iter(self):
            pass


def _release_db_connections() -> None:
    for conn in connections.all(initialized_only=True):
        if conn.connection is not None and not conn.in_atomic_block and conn.get_autocommit():
            conn.close_if_unusable_or_obsolete()


@overload
def release_db_connections(func: None = None) -> None: ...
@overload
def release_db_connections[F: Callable[..., Any]](func: F) -> F: ...
@overload
def release_db_connections[F: Callable[..., Any]](
    func: None = None, *, before: bool, after: bool = ...
) -> Callable[[F], F]: ...
@overload
def release_db_connections[F: Callable[..., Any]](func: None = None, *, after: bool) -> Callable[[F], F]: ...


def release_db_connections(
    func: Callable[..., Any] | None = None, *, before: bool | None = None, after: bool | None = None
) -> Any:
    """Releases current thread's database connections to the pool.

    Unlike Django's `close_old_connections`, this is safe to use inside a transaction block.

    Can be called directly, or used as a decorator to release connections before and/or after the decorated
    function is called. Defaults to releasing after.

        release_db_connections()

        @release_db_connections  # release after call
        @release_db_connections(before=True)  # release before and after each decorated function call
        @release_db_connections(before=True, after=False)  # release before each decorated function call
    """
    if func is None and before is None and after is None:
        _release_db_connections()
        return None

    release_before = True if before is None else before
    release_after = False if after is None else after

    def decorate[**P, R](decorated: Callable[P, R]) -> Callable[P, R]:
        @wraps(decorated)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            if release_before:
                _release_db_connections()
            try:
                return decorated(*args, **kwargs)
            finally:
                if release_after:
                    _release_db_connections()

        return wrapper

    if func is not None:
        return decorate(func)

    return decorate
