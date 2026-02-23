from urllib.parse import urlparse

from django.conf import settings
from django.core.cache import cache
from wagtail.models.sites import SITE_ROOT_PATHS_CACHE_KEY, SITE_ROOT_PATHS_CACHE_VERSION, Site, SiteRootPath


def replace_hostname(url: str) -> str:
    """Checks and replaces the hostname with an alternative."""
    parsed_url = urlparse(url)
    if not parsed_url.hostname:
        return url

    alternative = settings.CMS_HOSTNAME_ALTERNATIVES.get(parsed_url.hostname)
    if not alternative or alternative == parsed_url.hostname:
        return url

    replacement = f"{alternative}:{parsed_url.port}" if ":" in parsed_url.netloc else alternative
    parsed_url = parsed_url._replace(netloc=replacement)
    return parsed_url.geturl()


def get_mapped_site_root_paths(host: str | None = None) -> list[SiteRootPath]:
    """An expansion to Site.get_site_root_paths().

    Our version:
    - handles Sites mapped to localized root pages, rather than offer language alternatives for each Site.
    - expands to handle one Site with localized roots, like Site.get_site_root_paths
    - checks and replaces the base URL if the request is from one of the alternatives.
    """
    swap_domains: bool = host is not None and host in settings.CMS_HOSTNAME_ALTERNATIVES.values()
    cache_key = f"cms-{swap_domains}-{SITE_ROOT_PATHS_CACHE_KEY}"
    result = cache.get(cache_key, version=SITE_ROOT_PATHS_CACHE_VERSION)

    if result is None:
        result = []
        site = None

        for site in Site.objects.select_related("root_page", "root_page__locale").order_by(
            "-root_page__url_path", "-is_default_site", "hostname"
        ):
            result.append(
                SiteRootPath(
                    site.id,
                    site.root_page.url_path,
                    replace_hostname(site.root_url) if swap_domains else site.root_url,
                    site.root_page.locale.language_code,
                )
            )
        if len(result) == 1 and site:
            # If we have only one site, expand to include the translated root pages as alternatives
            # note: `and site` is not necessary per se, but added to silence mypy and avoid type ignores.
            for root_page in site.root_page.get_translations(inclusive=False).select_related("locale"):
                result.append(
                    SiteRootPath(
                        site.id,
                        root_page.url_path,
                        replace_hostname(site.root_url) if swap_domains else site.root_url,
                        root_page.locale.language_code,
                    )
                )

        cache.set(
            cache_key,
            result,
            3600,
            version=SITE_ROOT_PATHS_CACHE_VERSION,
        )

    else:
        # Convert the cache result to a list of SiteRootPath tuples, as some
        # cache backends (e.g. Redis) don't support named tuples.
        result = [SiteRootPath(*result) for result in result]

    return result
