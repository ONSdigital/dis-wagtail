from typing import TYPE_CHECKING

from django.db.models import Case, IntegerField, Value, When
from django.templatetags.static import static
from django.utils.html import format_html
from wagtail import hooks
from wagtail.admin import messages
from wagtail.admin.utils import get_valid_next_url_from_request

from cms.core.utils import redirect
from cms.home.models import HomePage
from cms.release_calendar.models import ReleaseCalendarIndex, ReleaseCalendarPage
from cms.release_calendar.viewsets import release_calendar_chooser_viewset

if TYPE_CHECKING:
    from django.http import HttpRequest, HttpResponsePermanentRedirect, HttpResponseRedirect
    from wagtail.models import Page
    from wagtail.query import PageQuerySet

    from .viewsets import FutureReleaseCalendarPageChooserViewSet

# Query keys that do not represent an active user-applied search or filter.
EXPLORER_IGNORED_QUERY_KEYS = {"_w_filter_fragment", "p"}

# Explorer views where the release calendar index should be pinned by default.
EXPLORER_VIEW_NAMES = {
    "wagtailadmin_explore",
    "wagtailadmin_explore_results",
}


@hooks.register("before_delete_page")
def before_delete_page(request: HttpRequest, page: Page) -> HttpResponseRedirect | HttpResponsePermanentRedirect | None:
    """Block release calendar page deletion and show a message."""
    if page.specific_class == ReleaseCalendarPage:
        if page.first_published_at is None:
            # Never published, so allow deletion as normal
            return None
        messages.warning(
            request, "Release Calendar pages cannot be deleted when published. You can mark them as cancelled instead."
        )
        return redirect("wagtailadmin_pages:edit", page.pk, preserve_request=False)

    if page.specific_class == ReleaseCalendarIndex:
        messages.warning(request, "The Release Calendar index cannot be deleted.")

        # redirect to a valid next url (passed via the 'next' query parameter)
        if next_url := get_valid_next_url_from_request(request):
            return redirect(next_url, preserve_request=False)

        # default to the Wagtail dashboard.
        return redirect("wagtailadmin_home", preserve_request=False)

    return None


@hooks.register("register_admin_viewset")
def register_chooser_viewset() -> FutureReleaseCalendarPageChooserViewSet:
    return release_calendar_chooser_viewset


@hooks.register("insert_editor_js")
def hide_release_date_text_field_for_non_provisional_release_pages() -> str:
    """Hide the release date text field for non-provisional release pages."""
    return format_html('<script src="{}"></script>', static("js/hide-date-text-on-non-provisional-releases.js"))


def _explorer_has_active_query(request: HttpRequest) -> bool:
    """Return whether the explorer request has any non-empty user query values."""
    for key, values in request.GET.lists():
        if key in EXPLORER_IGNORED_QUERY_KEYS:
            continue

        if any(value.strip() for value in values):
            return True

    return False


@hooks.register("construct_explorer_page_queryset")
def pin_release_calendar_page(parent_page: Page, pages: PageQuerySet, request: HttpRequest) -> PageQuerySet:
    """Pin the Release Calendar index to the top of the homepage explorer page."""
    # Only apply to the homepage Explorer view.
    resolver_match = getattr(request, "resolver_match", None)
    is_homepage_explorer = getattr(resolver_match, "view_name", "") in EXPLORER_VIEW_NAMES and isinstance(
        parent_page.specific_deferred, HomePage
    )

    if not is_homepage_explorer:
        return pages

    # Only pin on the default explorer view. Searches, filters, and sorting should use Wagtail's default ordering.
    if _explorer_has_active_query(request):
        return pages

    return pages.order_by(
        Case(
            When(content_type__model="releasecalendarindex", then=Value(0)),
            default=Value(1),
            output_field=IntegerField(),
        ),
        "-latest_revision_created_at",
    )
