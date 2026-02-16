from typing import TYPE_CHECKING, Any

from django.conf import settings
from django.db.models import IntegerField
from django.db.models.functions import Cast
from wagtail.contrib.frontend_cache.utils import purge_url_from_cache, purge_urls_from_cache
from wagtail.models import Page, ReferenceIndex, Site

from cms.articles.models import StatisticalArticlePage
from cms.methodology.models import MethodologyPage
from cms.standard_pages.models import InformationPage
from cms.topics.models import TopicPage

if TYPE_CHECKING:
    from django.db.models import Model


def get_page_cached_urls(page: Page, cache_object: Any | None = None) -> list[str]:
    """This is a modified version of core's get_page_cached_urls taking into account our no-trailing slash setup."""
    if (page_url := page.get_full_url(request=cache_object)) is None:
        # nothing to be done if the page has no routable URL
        return []

    return [
        f"{page_url.rstrip('/')}/{path.lstrip('/')}".rstrip("/") for path in page.specific_deferred.get_cached_paths()
    ]


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

    NOTE: To find urls for featuring multiple objects of the same type, use `get_urls_featuring_objects` instead.
    """
    return get_urls_featuring_objects([obj])


def get_urls_featuring_objects(objects: list[Model]) -> set[str]:
    """For multiple instances of the same model, return a set of URLs that make use of them in some way.

    This includes URLs for:
    -   Pages that directly reference the objects (e.g. via relationship fields
        or StreamField blocks)
    """
    urls: set[str] = set()

    if not objects:
        return urls

    object_ids = [int(obj.pk) for obj in objects]

    if isinstance(objects[0], Page):
        to_content_type_model = "page"
        to_content_type_app_label = "wagtailcore"
    else:
        to_content_type_model = objects[0]._meta.model_name.lower()  # type: ignore[union-attr]
        to_content_type_app_label = objects[0]._meta.app_label.lower()

    page_ids = (
        ReferenceIndex.objects.filter(
            base_content_type__model="page",
            base_content_type__app_label="wagtailcore",
            to_content_type__model=to_content_type_model,
            to_content_type__app_label=to_content_type_app_label,
            to_object_id__in=object_ids,
        )
        .annotate(page_id=Cast("object_id", output_field=IntegerField()))
        .values_list("page_id", flat=True)
    )

    # TODO: aliases
    for page in Page.objects.filter(id__in=page_ids).specific(defer=True).live().iterator():
        urls.update(get_page_cached_urls(page))

    return urls


def get_related_topic_page_urls(page: Page) -> set[str]:
    parent_topic = TopicPage.objects.ancestor_of(page).first().specific_deferred
    urls = set(get_page_cached_urls(parent_topic))

    related_topic_pages = TopicPage.objects.filter(topic__in=page.topic_ids).exclude(pk=parent_topic.pk).live().defer()

    # include parent topic translation aliases
    for parent_topic_alias in parent_topic.get_translations().filter(alias_of__isnull=False).specific(defer=True):
        urls.update(get_page_cached_urls(parent_topic_alias))
        related_topic_pages = related_topic_pages.exclude(pk=parent_topic_alias.pk)

    for topic_page in related_topic_pages:
        urls.update(get_page_cached_urls(topic_page))

    return urls


def purge_page_from_frontend_cache(page: Page) -> None:
    # get the page urls
    urls = set(get_page_cached_urls(page))

    # include translation aliases urls
    for translation in page.get_translations().filter(alias_of__isnull=False).specific(defer=True):
        urls.update(get_page_cached_urls(translation))

    # expand to custom logic
    if isinstance(page, StatisticalArticlePage):
        series_page = page.get_parent().specific_deferred
        urls.update(get_page_cached_urls(series_page))
        urls.update(get_related_topic_page_urls(series_page))
    elif isinstance(page, MethodologyPage):
        urls.update(get_related_topic_page_urls(page))
    elif isinstance(page, InformationPage):
        urls.update(get_page_cached_urls(page.get_parent().specific_deferred))

    urls.update(get_urls_featuring_object(page))
    purge_urls_from_cache(urls)


def purge_page_containing_snippet_from_cache(obj: Model) -> None:
    urls = get_urls_featuring_object(obj)
    purge_urls_from_cache(urls)
