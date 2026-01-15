from collections.abc import Mapping
from typing import TYPE_CHECKING

from django.contrib.auth.models import Permission
from django.shortcuts import redirect
from django.templatetags.static import static
from django.urls import include, reverse
from django.utils.html import format_html
from wagtail import hooks
from wagtail.admin import messages
from wagtail.admin.action_menu import PageLockedMenuItem, WorkflowMenuItem

from cms.bundles.mixins import BundledPageMixin
from cms.bundles.utils import in_bundle_ready_to_be_published

from . import admin_urls
from .action_menu import UnlockWorkflowMenuItem
from .admin_urls import path
from .utils import is_page_ready_to_publish

if TYPE_CHECKING:
    from django.db.models import QuerySet
    from django.http import HttpRequest, HttpResponse
    from django.urls import URLPattern
    from django.urls.resolvers import URLResolver
    from wagtail.admin.action_menu import ActionMenuItem
    from wagtail.models import Page


@hooks.register("construct_page_action_menu")
def amend_page_action_menu_items(menu_items: list[ActionMenuItem], request: HttpRequest, context: Mapping) -> None:
    if not (context["view"] == "edit" and context.get("page")):
        return

    if not isinstance(context["page"], BundledPageMixin):
        return

    updated_menu_items = menu_items
    page: Page = context["page"]
    if in_bundle_ready_to_be_published(page):
        # start with a fully locked action menu when in a bundle that is ready to be published,
        # as we want to prevent all actions.
        updated_menu_items = [PageLockedMenuItem()]

    if is_page_ready_to_publish(page):
        # The lock kicks in when we're in ReadyToPublishGroupTask, which marks the page as locked for editing.
        # this means none of the task actions are added to the menu, so we're adding them here.
        for name, label, launch_modal in page.current_workflow_task.get_actions(page, request.user):
            item_label = label
            if name == "unlock":
                url = reverse("workflows:unlock", args=(page.pk,))
                updated_menu_items.append(UnlockWorkflowMenuItem(name, label, icon_name="lock-open", item_url=url))
            else:
                icon_name = "success" if name == "approve" else "edit"
                updated_menu_items.append(WorkflowMenuItem(name, item_label, launch_modal, icon_name=icon_name))

    is_final_task = False
    if page.current_workflow_task:
        is_final_task = page.current_workflow_task.pk == page.current_workflow_state.workflow.tasks.last().pk

    for index, item in enumerate(updated_menu_items):
        if item.name != "approve":
            continue

        # tidy up the "approve" action label, both for when we're lock in ready to publish,
        # and when the workflow was "unlocked". i.e. moved back a step.
        label = "Approve" if "with comment" not in item.label else "Approve with comment"
        updated_menu_items[index].label = f"{label} and Publish" if is_final_task else label

    if page.latest_revision and page.latest_revision.user_id == request.user.pk:
        # hide the "approve" action items if the current user was the last editor as they cannot self-approve
        menu_items[:] = [item for item in updated_menu_items if item.name != "approve"]
    else:
        menu_items[:] = updated_menu_items


@hooks.register("construct_page_action_menu")
def amend_page_locked_action_menu_item(
    menu_items: list[ActionMenuItem], request: HttpRequest, context: Mapping
) -> None:
    # note: split into its own hook call to simplify the logic in amend_page_action_menu_items.
    if not (context["view"] == "edit" and context.get("page")):
        return

    if not isinstance(context["page"], BundledPageMixin):
        return

    for item in menu_items:
        if isinstance(item, PageLockedMenuItem):
            # ensure the page locked item is first
            item.order = -1
            menu_items.sort(key=lambda item: item.order)
            break


@hooks.register("before_edit_page")
def before_edit_page(request: HttpRequest, page: Page) -> HttpResponse | None:
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


@hooks.register("register_permissions")
def register_submit_translation_permission() -> QuerySet[Permission]:
    """Register the 'Unlock any workflow tasks' permission so it shows in the UI."""
    return Permission.objects.filter(content_type__app_label="wagtailadmin", codename="unlock_workflow_tasks")


@hooks.register("register_admin_urls")
def register_admin_urls() -> list[URLPattern | URLResolver]:
    """Registers the admin urls for custom workflow actions.

    @see https://docs.wagtail.org/en/stable/reference/hooks.html#register-admin-urls.
    """
    return [path("workflows/", include(admin_urls))]
