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


@hooks.register("construct_explorer_page_queryset")
def pin_release_calendar_page(_parent_page: Page, pages: PageQuerySet, _request: HttpRequest) -> PageQuerySet:
    """Pin the Release Calendar index to the top of the explorer page and explorer menu."""
    if all(isinstance(page.specific, HomePage) for page in pages):
        return pages.order_by("path")
    return pages.order_by(
        Case(
            When(content_type__model="releasecalendarindex", then=Value(0)),
            default=Value(1),
            output_field=IntegerField(),
        ),
        "-latest_revision_created_at",
    )
