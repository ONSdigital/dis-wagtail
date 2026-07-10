from typing import TYPE_CHECKING

from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.urls import reverse
from wagtail.admin import messages
from wagtail.models import Page

from cms.bundles.utils import in_bundle_ready_to_be_published
from cms.core.utils import redirect
from cms.users.models import User
from cms.workflows.models import GroupReviewTask, ReadyToPublishGroupTask

if TYPE_CHECKING:
    from django.http import HttpRequest
    from django.http.response import HttpResponsePermanentRedirect, HttpResponseRedirect


def unlock(
    request: HttpRequest, page_id: int
) -> TemplateResponse | HttpResponseRedirect | HttpResponsePermanentRedirect:
    """Return to draft view.

    Cancels the active workflow on the page, unlocking it for editing.
    Works for both the 'In Preview' (GroupReviewTask) and 'Ready to publish'
    (ReadyToPublishGroupTask) stages.
    """
    page = get_object_or_404(Page, id=page_id)
    if not page.permissions_for_user(request.user).can_edit():
        raise PermissionDenied

    page = page.specific_deferred

    if not isinstance(page.current_workflow_task, (GroupReviewTask, ReadyToPublishGroupTask)):
        raise PermissionDenied

    # Type ignore: request.user is guaranteed to be User by this point.
    user: User = request.user  # type: ignore[assignment]

    # Must be able to access the editor (i.e. be in the task groups or superuser)
    if not page.current_workflow_task.user_can_access_editor(page, user):
        raise PermissionDenied

    next_url = reverse("wagtailadmin_pages:edit", args=(page_id,))

    # Cannot return to draft if the page is in a bundle that is approved/ready to be published
    if in_bundle_ready_to_be_published(page):
        messages.error(
            request,
            f"Page '{page.get_admin_display_title()}' cannot be returned to draft as it "
            f"is included in a bundle that is ready to be published.",
        )
        return redirect(next_url, preserve_request=False)

    if request.method == "POST":
        with transaction.atomic():
            page.current_workflow_state.cancel(user=user)
            messages.success(request, f"Page '{page.get_admin_display_title()}' has been returned to draft.")

            return redirect(next_url, preserve_request=False)

    return TemplateResponse(
        request,
        "workflows/confirm_unlock.html",
        {
            "page": page,
            "next": next_url,
            "header_icon": "draft",
            "page_title": "Return to draft",
            "page_subtitle": page.get_admin_display_title(),
        },
    )
