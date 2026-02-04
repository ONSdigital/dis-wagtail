from collections.abc import Callable, Iterable
from functools import partial
from typing import TYPE_CHECKING

from cache_memoize import cache_memoize
from django.conf import settings
from django.views.decorators.cache import cache_control
from wagtail.contrib.frontend_cache.utils import _get_page_cached_urls, purge_url_from_cache
from wagtail.models import Page, ReferenceIndex, Site

from cms.images.models import CustomImage

if TYPE_CHECKING:
    from django.db.models import Model


def purge_cache_on_all_sites(path: str) -> None:
    """Purge the given path on all defined sites."""
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


memory_cache = partial(cache_memoize, cache_alias="memory")


def get_urls_featuring_object(obj: Model) -> set[str]:
    """For a single model instance, return a set of URLs that make use of the instance in some way.

    This includes URLs for:
    -   Pages that directly reference the object (e.g. via relationship fields
        or StreamField blocks)
    -   If the object is an image: Pages that directly reference a page
        that use the object as their listing image

    NOTE: To find urls for featuring multiple objects, use `get_urls_featuring_objects` instead.
    """
    urls = set()

    page_ids = [
        int(val)
        for val in ReferenceIndex.objects.filter(
            base_content_type__model="page",
            base_content_type__app_label="wagtailcore",
            to_content_type__model=obj._meta.model_name_lower,
            to_content_type__app_label=obj._meta.app_label_lower,
            to_object_id=obj.pk,
        ).values_list("object_id", flat=True)
    ]

    pages_with_listing_images = []
    for page in Page.objects.filter(id__in=page_ids).specific(defer=True).iterator():
        urls.update(_get_page_cached_urls(page))
        if isinstance(obj, CustomImage) and page.listing_image_id == obj.pk:
            pages_with_listing_images.append(page)

    urls.update(get_urls_featuring_objects(pages_with_listing_images))
    return urls


def get_urls_featuring_objects(objects: Iterable[Model]):
    """For multiple instances of the same model, return a set of URLs that make use of them in some way.

    This includes URLs for:
    -   Pages that directly reference the objects (e.g. via relationship fields
        or StreamField blocks)
    """
    urls = {}

    if not objects:
        return urls

    object_ids = [int(obj.pk) for obj in objects]

    page_ids = [
        int(val)
        for val in ReferenceIndex.objects.filter(
            base_content_type__model="page",
            base_content_type__app_label="wagtailcore",
            to_content_type__model=objects[0]._meta.model_name.lower(),
            to_content_type__app_label=objects[0]._meta.app_label.lower(),
            to_object_id__in=object_ids,
        ).values_list("object_id", flat=True)
    ]

    for page in Page.objects.filter(id__in=page_ids).specific(defer=True).iterator():
        urls.update(_get_page_cached_urls(page))

    return urls
