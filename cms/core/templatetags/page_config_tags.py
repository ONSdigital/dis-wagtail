from typing import TypedDict

import jinja2
from django.conf import settings
from django.core.cache import cache
from django.http import HttpRequest
from django.utils.translation import gettext_lazy as _
from wagtail.coreutils import WAGTAIL_APPEND_SLASH
from wagtail.models import Locale, Page, Site

from cms.core.models import BasePage
from cms.core.utils import deep_merge_mapping
from cms.locale.utils import get_mapped_site_root_paths
from cms.navigation.models import FooterMenu, MainMenu, NavigationSettings
from cms.navigation.utils import footer_menu_columns, main_menu_columns, main_menu_highlights


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


def _build_locale_urls(request: HttpRequest, page: BasePage) -> list[LocaleURLsDict]:
    """Build a list of locale URL mappings by preserving the current request path
    and swapping the language component (prefix or domain).

    This ensures routable sub-paths (e.g. /editions/, /related-data/) are preserved
    when switching language, rather than resolving to the page's canonical URL.
    """
    # TODO: if request.is_preview -> use view_draft URLs
    if prebuilt_locale_urls := getattr(page, "_locale_urls", None):
        return prebuilt_locale_urls  # type: ignore[no-any-return]

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


def get_hreflangs(request: HttpRequest, page: BasePage) -> list[HreflangDict]:
    """Returns a list of dictionaries containing URL and the full locale code.
    Typically used for HTML 'hreflang' tags.
    """
    # TODO make aware of subpage routing!
    base_urls = _build_locale_urls(request, page)
    return [{"url": item["url"], "lang": item["locale"].language_code} for item in base_urls]


def get_translation_urls(request: HttpRequest, page: BasePage) -> list[TranslationURLDict]:
    """Returns a list of dictionaries containing URL, ISO code, language name,
    and whether it is the current locale.
    """
    base_urls = _build_locale_urls(request, page)
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


def _strip_locale_prefix(path: str) -> str:
    """Strip any locale prefix from a URL path.

    e.g. "/cy/topic/articles" -> "/topic/articles", "/cy" -> "/".
    """
    for lang_code, _lang_name in settings.LANGUAGES:
        prefix = f"/{lang_code}/"
        if path.startswith(prefix):
            return path[len(f"/{lang_code}") :]
        if path == f"/{lang_code}":
            return "/"
    return path


def get_base_page_config_cache_key(site: Site, language_code: str) -> str:
    return f"_cms_base_page_config_cache_key_{site.pk}_{language_code}"


def _get_base_page_config(context: jinja2.runtime.Context, site: Site, request: HttpRequest) -> dict:
    is_preview = getattr(request, "is_preview", False)

    cache_key = get_base_page_config_cache_key(site, getattr(request, "LANGUAGE_CODE", settings.LANGUAGE_CODE))

    # Don't cache previews
    if not is_preview and (base_page_config := cache.get(cache_key)):
        return base_page_config  # type: ignore[no-any-return]

    navigation_settings = NavigationSettings.for_request(request)

    # NB: These variables from context are only used in preview, so this is safe to cache
    main_menu: MainMenu | None = context.get("main_menu") or (
        navigation_settings.main_menu.localized if navigation_settings.main_menu else None
    )
    footer_menu: FooterMenu | None = context.get("footer_menu") or (
        navigation_settings.footer_menu.localized if navigation_settings.footer_menu else None
    )

    base_page_config = {
        "header": {
            "variants": "basic",
            "phase": {"badge": _("Beta"), "html": _("This is a new service.")},
            "mastheadLogoUrl": "/",
            "menuLinks": {
                "id": "nav-links-external",
                "ariaLabel": _("Main menu"),
                "ariaListLabel": _("Main menu"),
                "toggleNavButton": {"text": _("Main menu"), "ariaLabel": _("Toggle main menu")},
                "keyLinks": main_menu_highlights(request, main_menu),
                "columns": main_menu_columns(request, main_menu),
            },
            "search": {"id": "search", "form": {"action": settings.ONS_WEBSITE_SEARCH_PATH, "inputName": "q"}},
        },
        "footer": {
            "cols": footer_menu_columns(request, footer_menu),
            "oglLink": {
                "pre": _("All content is available under the"),
                "text": "Open Government Licence v3.0",
                "url": "https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/",
                "post": _(", except where otherwise stated"),
            },
        },
    }

    if not is_preview:
        # Don't cache preview renders
        cache.set(cache_key, base_page_config)

    return base_page_config


def get_page_config_cache_key(site: Site, page: Page, language_code: str) -> str:
    return f"_cms_page_config_cache_key_{page.pk}_{site.pk}_{language_code}"


def _add_site_name_to_page_title(page_title: str, site: Site, is_homepage: bool) -> str:
    if not site.site_name:
        return page_title

    if is_homepage:
        return f"{site.site_name} - {page_title}"

    return f"{page_title} - {site.site_name}"


def _get_page_config(context: jinja2.runtime.Context, page: BasePage | None, site: Site, request: HttpRequest) -> dict:
    absolute_url = request.build_absolute_uri()

    # If there's no page, use sensible defaults
    if page is None:
        return {
            "bodyClasses": "",
            "title": _add_site_name_to_page_title(context.get("page_title", ""), site, False),
            "header": {"language": {"languages": []}},
            "meta": {"hrefLangs": [], "canonicalUrl": absolute_url},
            "absoluteUrl": absolute_url,
        }

    is_preview = getattr(request, "is_preview", False)
    cache_key = get_page_config_cache_key(site, page, getattr(request, "LANGUAGE_CODE", settings.LANGUAGE_CODE))

    # Don't cache previews
    page_config = cache.get(cache_key) if not is_preview else None

    is_homepage = page.pk == site.root_page_id

    if page_config is None:
        page_title: str = page.seo_title or getattr(page, "display_title", page.title)  # type: ignore[assignment]

        page_title = _add_site_name_to_page_title(page_title, site, is_homepage)

        page_config = {
            "bodyClasses": "template-" + page._meta.verbose_name.lower().replace(" ", "-"),  # type: ignore[union-attr]
            "title": page_title,
            "header": {"language": {"languages": get_translation_urls(request, page)}},
            "meta": {
                "hrefLangs": get_hreflangs(request, page),
                "canonicalUrl": page.get_canonical_url(request),
            },
        }

        if not is_preview:
            cache.set(cache_key, page_config)

    # Let page context override the page title.
    # This is intentionally not cached as it varies by context.
    if page_title_from_context := context.get("page_title"):
        page_config["title"] = _add_site_name_to_page_title(page_title_from_context, site, is_homepage)

    # Set absolute URL outside the cache to support routable pages
    page_config["absoluteUrl"] = absolute_url

    return page_config


@jinja2.pass_context
def get_page_config(context: jinja2.runtime.Context) -> dict:
    page: BasePage | None = context.get("page")
    request = context["request"]
    site: Site = Site.find_for_request(request)

    # Merge the base and page-specific config, so they can be cached (and invalidated) independently.
    # Page config is passed first so it can take precedence.
    return deep_merge_mapping(
        _get_page_config(context, page, site, request),
        _get_base_page_config(context, site, request),
    )
