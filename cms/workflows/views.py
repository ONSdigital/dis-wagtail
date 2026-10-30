from typing import TYPE_CHECKING

from django.urls import reverse

from cms.core.utils import redirect

if TYPE_CHECKING:
    from django.http import HttpRequest
    from django.http.response import HttpResponsePermanentRedirect, HttpResponseRedirect


def unlock(request: HttpRequest, page_id: int) -> HttpResponseRedirect | HttpResponsePermanentRedirect:
    """Legacy unlock view — no longer needed.

    'Unlock editing' is now handled via the standard Wagtail reject action on both workflow tasks.
    This view redirects to the page edit view for backwards compatibility (e.g. bookmarked URLs).
    """
    return redirect(reverse("wagtailadmin_pages:edit", args=(page_id,)), preserve_request=False)
