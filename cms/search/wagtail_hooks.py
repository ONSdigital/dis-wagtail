from wagtail import hooks

from . import get_publisher

publisher = get_publisher()


def _should_exclude_page(page):
    return page.__class__.__name__ in EXCLUDED_PAGE_TYPES


@hooks.register("after_publish_page")
def page_published(request, page):
    """This hook is called after a page is published from the Wagtail admin."""
    if _should_exclude_page(page):
        return
    publisher.publish_created_or_updated(page)


@hooks.register("after_unpublish_page")
def page_unpublished(request, page):
    """This hook is called after a page is unpublished from the Wagtail admin."""
    if _should_exclude_page(page):
        return
    publisher.publish_deleted(page)


EXCLUDED_PAGE_TYPES = (
    "HomePage",
    "ArticleSeriesPage",
    "ReleaseCalendarIndex",
    "ThemePage",
    "TopicPage",
)
