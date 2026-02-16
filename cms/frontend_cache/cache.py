from collections.abc import Iterable
from typing import TYPE_CHECKING

from django.conf import settings
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
