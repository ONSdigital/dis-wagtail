from typing import TYPE_CHECKING, Optional

from django.shortcuts import redirect
from wagtail import hooks
from wagtail.admin import messages
from wagtail.admin.utils import get_valid_next_url_from_request

from cms.release_calendar.models import ReleaseCalendarIndex, ReleaseCalendarPage
from cms.release_calendar.viewsets import release_calendar_chooser_viewset

if TYPE_CHECKING:
    from django.http import HttpRequest, HttpResponseRedirect
    from wagtail.models import Page

    from .viewsets import FutureReleaseCalendarPageChooserViewSet


@hooks.register("before_delete_page")
def before_delete_page(request: "HttpRequest", page: "Page") -> Optional["HttpResponseRedirect"]:
    """Block release calendar page deletion and show a message."""
    if page.specific_class == ReleaseCalendarPage:
        messages.warning(request, "Release Calendar pages cannot be deleted. You can mark them as cancelled instead.")
        return redirect("wagtailadmin_pages:edit", page.pk)

    if page.specific_class == ReleaseCalendarIndex:
        messages.warning(request, "The Release Calendar index cannot be deleted.")

        # redirect to a valid next url (passed via the 'next' query parameter)
        if next_url := get_valid_next_url_from_request(request):
            return redirect(next_url)

        # default to the Wagtail dashboard.
        return redirect("wagtailadmin_home")

    return None


@hooks.register("register_admin_viewset")
def register_chooser_viewset() -> "FutureReleaseCalendarPageChooserViewSet":
    return release_calendar_chooser_viewset
