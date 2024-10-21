from collections.abc import Callable

from django.conf import settings
from django.views.decorators.cache import cache_control
from wagtail.contrib.frontend_cache.utils import purge_url_from_cache
from wagtail.models import Site


def purge_cache_on_all_sites(path: str) -> None:
    if settings.DEBUG:
        return

    for site in Site.objects.all():
        purge_url_from_cache(site.root_url.rstrip("/") + path)


def get_default_cache_control_kwargs() -> dict[str, int | bool]:
    """Get cache control parameters used by the cache control decorators
    used by default on most pages. These parameters are meant to be
    sane defaults that can be applied to a standard content page.
    """
    s_maxage = getattr(settings, "CACHE_CONTROL_S_MAXAGE", None)
    stale_while_revalidate = getattr(settings, "CACHE_CONTROL_STALE_WHILE_REVALIDATE", None)
    cache_control_kwargs = {
        "s_maxage": s_maxage,
        "stale_while_revalidate": stale_while_revalidate,
        "public": True,
    }
    return {k: v for k, v in cache_control_kwargs.items() if v is not None}


def get_default_cache_control_decorator() -> Callable:
    """Get cache control decorator that can be applied to views as a
    sane default for normal content pages.
    """
    cache_control_kwargs = get_default_cache_control_kwargs()
    return cache_control(**cache_control_kwargs)
