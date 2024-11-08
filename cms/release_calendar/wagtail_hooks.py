from typing import TYPE_CHECKING, Optional

from django.shortcuts import redirect
from django.utils.translation import gettext as _
from wagtail import hooks
from wagtail.admin import messages
from wagtail.admin.utils import get_valid_next_url_from_request

from cms.release_calendar.models import ReleaseCalendarIndex, ReleaseCalendarPage

if TYPE_CHECKING:
    from django.http import HttpRequest, HttpResponseRedirect
    from wagtail.models import Page


@hooks.register("before_delete_page")
def before_delete_page(request: "HttpRequest", page: "Page") -> Optional["HttpResponseRedirect"]:
    """Block release calendar page deletion and show a message."""
    if page.specific_class == ReleaseCalendarPage:
        messages.warning(
            request, _("Release Calendar pages cannot be deleted. You can mark them as cancelled instead.")
        )
        return redirect("wagtailadmin_pages:edit", page.pk)

    if page.specific_class == ReleaseCalendarIndex:
        messages.warning(request, _("The Release Calendar index cannot be deleted."))

        # redirect to a valid next url (passed via the 'next' query parameter)
        if next_url := get_valid_next_url_from_request(request):
            return redirect(next_url)

        # default to the Wagtail dashboard.
        return redirect("wagtailadmin_home")

    return None
