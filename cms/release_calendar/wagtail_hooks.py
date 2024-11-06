from typing import TYPE_CHECKING, Optional

from django.shortcuts import redirect
from wagtail import hooks
from wagtail.admin import messages

from cms.release_calendar.models import ReleaseCalendarPage

if TYPE_CHECKING:
    from django.http import HttpRequest, HttpResponseRedirect
    from wagtail.models import Page


@hooks.register("before_delete_page")
def before_delete_page(request: "HttpRequest", page: "Page") -> Optional["HttpResponseRedirect"]:
    """Block release calendar page deletion and show a message."""
    if request.method == "POST" and page.specific_class == ReleaseCalendarPage:
        messages.warning(request, "Release calendar pages cannot be deleted. You can mark them as cancelled instead.")

        return redirect("wagtailadmin_pages:edit", page.pk)

    return None
