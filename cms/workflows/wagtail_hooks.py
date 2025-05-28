from collections.abc import Mapping
from typing import TYPE_CHECKING, Optional

from django.shortcuts import redirect
from django.templatetags.static import static
from django.utils.html import format_html
from wagtail import hooks
from wagtail.admin import messages

from cms.bundles.mixins import BundledPageMixin

if TYPE_CHECKING:
    from django.http import HttpRequest, HttpResponse
    from wagtail.admin.action_menu import ActionMenuItem
    from wagtail.models import Page


@hooks.register("construct_page_action_menu")
def amend_page_action_menu_items(menu_items: list["ActionMenuItem"], request: "HttpRequest", context: Mapping) -> None:
    if not (context["view"] == "edit" and context.get("page")):
        return

    page: Page = context["page"]
    if not isinstance(page, BundledPageMixin):
        return

    if page.latest_revision and page.latest_revision.user_id == request.user.pk:  # type: ignore[attr-defined]
        # hide the "approve" action items if the current user was the last editor
        menu_items[:] = [item for item in menu_items if item.name != "approve"]


@hooks.register("before_edit_page")
def before_edit_page(request: "HttpRequest", page: "Page") -> Optional["HttpResponse"]:
    if (
        request.method != "POST"
        or request.POST.get("action-workflow-action") != "true"
        or request.POST.get("workflow-action-name") != "approve"
        or page.latest_revision.user_id != request.user.pk
    ):
        return None

    messages.error(request, "Cannot self-approve your changes. Please ask another Publishing team member to do so.")
    return redirect("wagtailadmin_pages:edit", page.pk)


@hooks.register("insert_editor_js")
def insert_workflow_tweaks_js() -> str:
    return format_html('<script src="{}"></script>', static("js/workflow-tweaks.js"))
