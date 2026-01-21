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
from cms.bundles.utils import in_active_bundle, in_bundle_ready_to_be_published

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


def update_action_menu(menu_items: list[ActionMenuItem], request: HttpRequest, context: Mapping) -> list:
    """Modifies the action menu items depending on the page state.

    - if the page is in a bundle that is ready to be published, remove all actions regardless of permissions
    - when the page is ready to be published, it is locked for editing, so inject the ReadyToPublishTask actions
    - hide the "approve" tasks for the last editor
    - and finally tidy up the "approve" labels
    """
    updated_menu_items = menu_items
    page: Page = context["page"]
    if in_bundle_ready_to_be_published(page):
        # start with a fully locked action menu when in a bundle that is ready to be published,
        # as we want to prevent all actions.
        return [PageLockedMenuItem()]

    if is_page_ready_to_publish(page):
        # The lock kicks in when we're in ReadyToPublishGroupTask, which marks the page as locked for editing.
        # this means none of the task actions are added to the menu, so we're adding them here.
        for name, label, launch_modal in page.current_workflow_task.get_actions(page, request.user):
            item_label = label
            if name == "unlock":
                url = reverse("workflows:unlock", args=(page.pk,))
                updated_menu_items.append(UnlockWorkflowMenuItem(name, label, icon_name="lock-open", item_url=url))
            else:
                icon_name = "success" if name in ["approve", "locked-approve"] else "edit"
                updated_menu_items.append(WorkflowMenuItem(name, item_label, launch_modal, icon_name=icon_name))

    is_final_task = (
        page.current_workflow_task
        and page.current_workflow_task.pk == page.current_workflow_state.workflow.tasks.last().pk
    )

    is_self_approver = page.latest_revision and page.latest_revision.user_id == request.user.pk
    final_menu_items = []
    for item in updated_menu_items:
        if item.name in ["approve", "locked-approve"]:
            # skip adding this item when the current user was the last editor to prevent self-approval
            if is_self_approver:
                continue

            # tidy up the "approve" action label, both for when we're lock in ready to publish,
            # and when the workflow was "unlocked". i.e. moved back a step.
            if is_final_task:
                label = "Publish" if "with comment" not in item.label else "Publish with comment"
            else:
                label = "Approve" if "with comment" not in item.label else "Approve with comment"
            item.label = label
        final_menu_items.append(item)

    return final_menu_items


@hooks.register("construct_page_action_menu")
def amend_page_action_menu_items(menu_items: list[ActionMenuItem], request: HttpRequest, context: Mapping) -> None:
    if not (context["view"] == "edit" and context.get("page")):
        return

    if not isinstance(context["page"], BundledPageMixin):
        return

    # do the bulk of tweaks
    updated_menu_items = update_action_menu(menu_items, request, context)

    # finally ensure the page locked item is first
    for item in updated_menu_items:
        if isinstance(item, PageLockedMenuItem):
            item.order = -1
            updated_menu_items.sort(key=lambda item: item.order)
            break

    menu_items[:] = updated_menu_items


@hooks.register("before_edit_page")
def before_edit_page(request: HttpRequest, page: Page) -> HttpResponse | None:
    if request.method != "POST" or request.POST.get("action-workflow-action") != "true":
        return None

    action_name = request.POST.get("workflow-action-name", "")

    if action_name == "approve" and page.latest_revision.user_id == request.user.pk:
        messages.error(request, "Cannot self-approve your changes. Please ask another Publishing team member to do so.")
        return redirect("wagtailadmin_pages:edit", page.pk)

    if action_name == "locked-approve" and is_page_ready_to_publish(page) and not in_active_bundle(page):
        # The page is "Ready to publish" and the edit form was POSTed with the ReadyToPublishGroupTask "locked-approve"
        # action. Perform the required workflow action without saving the form.
        # Note: this follows the logic from the Wagtail core page edit view
        # https://github.com/wagtail/wagtail/blob/40c9b1fdff19bad5b9997c0366ed5cb642edd557/wagtail/admin/views/pages/edit.py#L854
        page.current_workflow_task.on_action(page.current_workflow_task_state, request.user, action_name)

        # run the after_edit_page hook
        for fn in hooks.get_hooks("after_edit_page"):
            result = fn(request, page)
            if hasattr(result, "status_code"):
                typed_result: HttpResponse = result  # placate mypy
                return typed_result

        message = f"Page '{page.get_admin_display_title()}' has been published."

        buttons = []
        if (page_url := page.get_url(request=request)) is not None:
            buttons.append(messages.button(page_url, "View live", new_window=False))
        buttons.append(messages.button(reverse("wagtailadmin_pages:edit", args=(page.pk,)), "Edit"))
        messages.success(request, message, buttons=buttons)

        return redirect("wagtailadmin_explore", page.get_parent().pk)

    return None


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
