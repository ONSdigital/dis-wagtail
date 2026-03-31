from datetime import datetime
from typing import TYPE_CHECKING, Any, TypedDict

import jinja2
from django import template
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import json_script as _json_script
from django_jinja import library
from wagtail.contrib.routable_page.templatetags.wagtailroutablepage_tags import routablepageurl
from wagtail.coreutils import WAGTAIL_APPEND_SLASH
from wagtail.models import Locale, Page

from cms.core.custom_date_format import ons_date_format
from cms.locale.utils import get_mapped_site_root_paths

register = template.Library()

if TYPE_CHECKING:
    from django.utils.safestring import SafeString


class LocaleURLsDict(TypedDict):
    locale: Locale
    url: str


class TranslationURLDict(TypedDict):
    url: str
    isoCode: str
    text: str
    current: bool


class HreflangDict(TypedDict):
    url: str
    lang: str


@library.global_function
@jinja2.pass_context
def include_django(context: jinja2.runtime.Context, template_name: str) -> SafeString:
    """Allow importing a pre-rendered Django template into jinja2."""
    return render_to_string(template_name, context=dict(context), request=context.get("request", None))


def set_attributes_filter(attributes: dict, new_attributes: dict) -> dict:
    """Update attributes dictionary with new_attributes.
    This is a Python reimplementation of the Nunjucks setAttributes filter.
    See:
    https://github.com/ONSdigital/design-system/blob/d4d4e171690141678af022379273f1e408f5a4e3/lib/filters/set-attributes.js#L1-L9
    Usage in template: {{ attributes|setAttributes(new_attributes) }}.
    """
    attributes.update(new_attributes)
    return attributes


def _strip_locale_prefix(path: str) -> str:
    """Strip any locale prefix from a URL path.

    e.g. "/cy/topic/articles" -> "/topic/articles", "/cy" -> "/".
    """
    for lang_code, _ in settings.LANGUAGES:
        prefix = f"/{lang_code}/"
        if path.startswith(prefix):
            return path[len(f"/{lang_code}") :]
        if path == f"/{lang_code}":
            return "/"
    return path


def _build_locale_urls(context: jinja2.runtime.Context) -> list[LocaleURLsDict]:
    """Build a list of locale URL mappings by preserving the current request path
    and swapping the language component (prefix or domain).

    This ensures routable sub-paths (e.g. /editions/, /related-data/) are preserved
    when switching language, rather than resolving to the page's canonical URL.
    """
    page = context.get("page")
    if not page:
        return []

    # TODO: if request.is_preview -> use view_draft URLs
    if prebuilt_locale_urls := getattr(page, "_locale_urls", None):
        return prebuilt_locale_urls  # type: ignore[no-any-return]

    request = context["request"]
    request_path = request.path
    use_subdomain_locale = settings.CMS_USE_SUBDOMAIN_LOCALES
    results: list[LocaleURLsDict] = []

    if use_subdomain_locale:
        # Subdomain mode: preserve request path, swap domain
        site_root_paths = get_mapped_site_root_paths(host=request.get_host())
        locale_root_urls: dict[str, str] = {}
        for srp in site_root_paths:
            if srp.language_code not in locale_root_urls:
                locale_root_urls[srp.language_code] = srp.root_url

        for locale in Locale.objects.all().order_by("pk"):
            root_url = locale_root_urls.get(locale.language_code)
            if not root_url:
                continue
            results.append({"locale": locale, "url": f"{root_url}{request_path}"})
    else:
        # Path-based mode: preserve request path, swap locale prefix
        default_locale = Locale.get_default()
        bare_path = _strip_locale_prefix(request_path)

        for locale in Locale.objects.all().order_by("pk"):
            if locale.pk == default_locale.pk:
                url = bare_path
            elif bare_path == "/":
                url = f"/{locale.language_code}/" if WAGTAIL_APPEND_SLASH else f"/{locale.language_code}"
            else:
                url = f"/{locale.language_code}{bare_path}"
            results.append({"locale": locale, "url": url})

    page._locale_urls = results  # pylint: disable=protected-access

    return results


@jinja2.pass_context
def get_translation_urls(context: jinja2.runtime.Context) -> list[TranslationURLDict]:
    """Returns a list of dictionaries containing URL, ISO code, language name,
    and whether it is the current locale.
    """
    base_urls = _build_locale_urls(context)
    urls: list[TranslationURLDict] = []
    for item in base_urls:
        locale = item["locale"]
        urls.append(
            {
                "url": item["url"],
                "isoCode": locale.language_code.split("-", 1)[0],
                "text": ("English" if locale.language_name_local == "British English" else locale.language_name_local),
                "current": locale.is_active,
            }
        )
    return urls


@jinja2.pass_context
def get_hreflangs(context: jinja2.runtime.Context) -> list[HreflangDict]:
    """Returns a list of dictionaries containing URL and the full locale code.
    Typically used for HTML 'hreflang' tags.
    """
    # TODO make aware of subpage routing!
    base_urls = _build_locale_urls(context)
    hreflangs: list[HreflangDict] = [{"url": item["url"], "lang": item["locale"].language_code} for item in base_urls]
    return hreflangs


@register.filter(name="ons_date")
def ons_date_format_filter(value: datetime | None, format_string: str) -> str:
    """Format a date using the ons_date_format function."""
    return "" if value is None else ons_date_format(value, format_string)


# Copy django's json_script filter
@register.filter(is_safe=True)
def json_script(value: dict[str, Any], element_id: str | None = None) -> SafeString:
    """Output value JSON-encoded, wrapped in a <script type="application/json">
    tag (with an optional id).
    """
    return _json_script(value, element_id)


def extend(value: list[Any], element: Any) -> None:
    """Append an item to a list.

    This could be achieved in Nunjucks with array.concat(item), and in Jinja2
    with array.append(item), but not with any syntax that is available in both.

    Use:
        {% set _ = extend(series, seriesItem) %}

    There is no actual return value, but the `set` tag should be used to avoid
    printing to the template.
    """
    if not isinstance(value, list):
        # This function is likely to be called from a template macro, so we
        # can't rely on annotations and tooling for type safety.
        raise TypeError("First argument must be a list.")
    return value.append(element)


@register.filter(name="routablepageurl")
def routablepageurl_no_trailing_slash(
    context: jinja2.runtime.Context,
    page: Page,
    *args: Any,
    **kwargs: Any,
) -> Any:
    """Overwrite Wagtail's routablepageurl to remove trailing slash."""
    return routablepageurl(context, page, *args, **kwargs).rstrip("/")
