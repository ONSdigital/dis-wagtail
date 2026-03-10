from typing import TYPE_CHECKING, Any

from django.conf import settings
from django.db.models import IntegerField, Q
from django.db.models.functions import Cast
from wagtail.contrib.frontend_cache.utils import purge_urls_from_cache
from wagtail.coreutils import get_dummy_request
from wagtail.models import Locale, Page, ReferenceIndex, Site

from cms.articles.models import ArticleSeriesPage, StatisticalArticlePage
from cms.methodology.models import MethodologyPage
from cms.standard_pages.models import InformationPage
from cms.topics.models import TopicPage

if TYPE_CHECKING:
    from django.db.models import Model


def get_page_cached_urls(page: Page, cache_object: Any | None = None) -> list[str]:
    """This is a modified version of core's get_page_cached_urls taking into account our no-trailing slash setup.

    See https://github.com/wagtail/wagtail/issues/13920
    """
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

    urls = [site.root_url.rstrip("/") + path for site in Site.objects.all()]
    purge_urls_from_cache(urls)


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

    for page in (
        Page.objects.filter(Q(id__in=page_ids) | Q(alias_of__in=page_ids)).specific(defer=True).live().iterator()
    ):
        urls.update(get_page_cached_urls(page))

    return urls


def get_related_topic_page_urls(page: Page, topic_ids: list[str] | None = None) -> set[str]:
    if page.alias_of_id is not None:
        # skip if the given page is an alias. Aliases are not published directly, but
        # via their source page, which then accounts for related topics and their aliases.
        return set()

    parent_topic = TopicPage.objects.ancestor_of(page).first().specific_deferred
    urls = set(get_page_cached_urls(parent_topic))

    topic_terms = topic_ids or getattr(page, "topic_ids", [])
    related_topic_pages = TopicPage.objects.filter(topic__in=topic_terms).exclude(pk=parent_topic.pk).live().defer()

    # include parent topic translation aliases
    for parent_topic_alias in parent_topic.get_translations().filter(alias_of__isnull=False).specific(defer=True):
        urls.update(get_page_cached_urls(parent_topic_alias))
        related_topic_pages = related_topic_pages.exclude(pk=parent_topic_alias.pk)

    for topic_page in related_topic_pages:
        urls.update(get_page_cached_urls(topic_page))

    return urls


def get_topic_pages_featuring_series(
    statistical_article: StatisticalArticlePage, article_series: ArticleSeriesPage
) -> set[str]:
    """Returns the list of topic page URLs that feature the given statistical article series."""
    urls = set()

    if not statistical_article.is_latest:
        return urls

    topic_page_ids = []
    # Get the series topic path and exclude it as we handle the parent topic separately.
    # url_path is in the form: /home/topic/articles/series/ so this becomes /home/topic/
    parent_topic_path = "/".join(article_series.url_path.rstrip("/").split("/")[:-2]) + "/"
    for topic_page in article_series.featured_on_topic.live().exclude(path=parent_topic_path).only("pk", "url_path"):
        urls.update(get_page_cached_urls(topic_page))
        topic_page_ids.append(topic_page.pk)

    for topic_page_alias in TopicPage.objects.filter(alias_of__in=topic_page_ids).only("pk", "url_path"):
        urls.update(get_page_cached_urls(topic_page_alias))

    return urls


def _get_welsh_alias_urls(source_page_ids: set) -> set[str]:
    urls = set()
    # Include Welsh aliases in this too.
    # Also, since we don't have a request here, get a dummy one for the Welsh pages.
    welsh_locale_id = Locale.objects.filter(language_code="cy").values_list("pk", flat=True)[0]
    cache_object = get_dummy_request(site=Site.objects.filter(root_page__locale=welsh_locale_id).first())
    for alias in Page.objects.filter(locale=welsh_locale_id, alias_of__in=source_page_ids).specific().iterator():
        urls.update(get_page_cached_urls(alias, cache_object=cache_object))

    return urls


def get_old_page_slugs(page: Page, page_old: Page, include_welsh_aliases: bool = True) -> set[str]:
    urls: set = set()
    if page.url_path == page_old.url_path:
        return urls

    url_path_length = len(page.url_path)

    # include the old page URL
    urls = set(get_page_cached_urls(page_old))
    source_page_ids = {page_old.pk}

    for descendant in page.get_descendants().live().defer_streamfields().specific().iterator():
        source_page_ids.add(descendant.pk)
        descendant.url_path = page_old.url_path + descendant.url_path[url_path_length:]

        urls.update(get_page_cached_urls(descendant))

    if include_welsh_aliases:
        urls |= _get_welsh_alias_urls(source_page_ids)

    return urls


def purge_page_from_frontend_cache(page: Page) -> None:
    # get the page urls
    urls = set(get_page_cached_urls(page))

    # expand to custom logic
    if isinstance(page, StatisticalArticlePage):
        series_page = page.get_parent().specific_deferred
        urls.update(get_page_cached_urls(series_page))
        urls.update(get_related_topic_page_urls(series_page))
        urls.update(get_topic_pages_featuring_series(page, series_page))
    elif isinstance(page, MethodologyPage):
        urls.update(get_related_topic_page_urls(page))
    elif isinstance(page, InformationPage):
        urls.update(get_page_cached_urls(page.get_parent().specific_deferred))

    urls.update(get_urls_featuring_object(page))
    purge_urls_from_cache(urls)


def purge_old_page_slugs_from_frontend_cache(page: Page, page_old: Page, include_welsh_aliases: bool = True) -> None:
    if urls := get_old_page_slugs(page, page_old, include_welsh_aliases):
        purge_urls_from_cache(urls)


def purge_old_page_paths_from_cache_after_move(
    page: Page, parent_page_before: Page, parent_page_after: Page, url_path_before: str
) -> None:
    if page.url_path == url_path_before:
        # This is a page 'reorder' within the same parent. No need for further processing
        return

    # Simulate an 'old_page' by copying the specific instance and resetting
    # the in-memory `url_path` value to what it was before the move
    old_page = type(page)()
    old_page.__dict__.update(page.__dict__)
    old_page.url_path = url_path_before

    urls = get_old_page_slugs(page, old_page, include_welsh_aliases=False)
    if isinstance(page, StatisticalArticlePage):
        urls.update(get_page_cached_urls(parent_page_before))  # old series
        urls.update(get_related_topic_page_urls(parent_page_before))  # old topic

        urls.update(get_page_cached_urls(parent_page_after))  # new series
        urls.update(get_related_topic_page_urls(parent_page_after))  # new topic
    elif isinstance(page, ArticleSeriesPage):
        urls.update(get_related_topic_page_urls(page))
        # the parent is the article index so doesn't have any topic IDs.
        urls.update(get_related_topic_page_urls(parent_page_before, topic_ids=page.topic_ids))
    elif isinstance(page, MethodologyPage):
        urls.update(get_related_topic_page_urls(page))
        urls.update(get_related_topic_page_urls(parent_page_before, topic_ids=page.topic_ids))
    elif isinstance(page, InformationPage):
        urls.update(get_page_cached_urls(parent_page_before))
        urls.update(get_page_cached_urls(parent_page_after))

    if urls:
        purge_urls_from_cache(urls)


def purge_series_children_from_cache(page: ArticleSeriesPage) -> None:
    # when an article series title changes, we want to purge all child articles too
    # so they get the updated title
    urls = set()
    source_page_ids = set()
    for child in page.get_descendants().live().specific(defer=True).iterator():
        source_page_ids.add(child.pk)
        urls.update(get_page_cached_urls(child))

    urls |= _get_welsh_alias_urls(source_page_ids)

    if urls:
        purge_urls_from_cache(urls)


def purge_page_containing_snippet_from_cache(obj: Model) -> None:
    if urls := get_urls_featuring_object(obj):
        purge_urls_from_cache(urls)
