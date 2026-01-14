from typing import TYPE_CHECKING, cast

from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.urls import reverse
from wagtail.admin import messages
from wagtail.models import Page

from cms.users.models import User
from cms.workflows.models import ReadyToPublishGroupTask

if TYPE_CHECKING:
    from django.http import HttpRequest
    from django.http.response import HttpResponseRedirect


def unlock(request: HttpRequest, page_id: int) -> TemplateResponse | HttpResponseRedirect:
    page = get_object_or_404(Page, id=page_id)
    if not page.permissions_for_user(request.user).can_edit():
        raise PermissionDenied

    page = page.specific_deferred

    if not isinstance(page.current_workflow_task, ReadyToPublishGroupTask):
        raise PermissionDenied

    user = cast(User, request.user)  # placates mypy complaining about AnonymousUser. We know this is a proper user
    if not page.current_workflow_task.user_can_unlock_for_edits(page, user):
        # the user must be able to action ReadyToPublishGroupTask, and the page must not be in a bundle that
        # is ready to be published
        raise PermissionDenied

    next_url = reverse("wagtailadmin_pages:edit", args=(page_id,))
    if request.method == "POST":
        with transaction.atomic():
            page.current_workflow_task.on_action(page.current_workflow_task_state, user, "unlock")
            messages.success(request, "Page editing unlocked.")

            return redirect(next_url)

    return TemplateResponse(
        request,
        "workflows/confirm_unlock.html",
        {
            "page": page,
            "next": next_url,
            "header_icon": "lock-open",
            "page_title": "Unlock",
            "page_subtitle": page.get_admin_display_title(),
        },
    )
