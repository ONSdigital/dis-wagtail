import json
from collections.abc import Mapping
from typing import TYPE_CHECKING

from django.contrib.auth.models import Permission
from django.templatetags.static import static
from django.urls import include, reverse
from django.utils import timezone
from django.utils.html import format_html
from wagtail import hooks
from wagtail.admin import messages
from wagtail.admin.action_menu import PageLockedMenuItem, WorkflowMenuItem

from cms.bundles.utils import in_active_bundle, in_bundle_ready_to_be_published
from cms.core.utils import redirect

from . import admin_urls
from .action_menu import SubmitForModerationMenuItem
from .admin_urls import path
from .models import get_final_approve_label
from .utils import is_page_in_workflow, is_page_ready_to_publish

if TYPE_CHECKING:
    from django.db.models import QuerySet
    from django.http import HttpRequest, HttpResponse
    from django.urls import URLPattern
    from django.urls.resolvers import URLResolver
    from wagtail.admin.action_menu import ActionMenuItem
    from wagtail.models import Page


def _perform_workflow_action_on_locked_page(request: HttpRequest, page: Page, action_name: str) -> HttpResponse | None:
    """Perform a workflow action on a locked page without saving the form.

    Since both workflow tasks lock the page (locked_for_user=True), Wagtail's edit view
    rejects all POSTs with 'The page could not be saved as it is locked.' We intercept
    workflow actions in before_edit_page and perform them directly.
    """
    extra_workflow_data_json = request.POST.get("workflow-action-extra-data", "{}")
    try:
        extra_workflow_data = json.loads(extra_workflow_data_json)
    except (json.JSONDecodeError, TypeError):
        extra_workflow_data = {}
    page.current_workflow_task.on_action(
        page.current_workflow_task_state, request.user, action_name, **extra_workflow_data
    )

    # run the after_edit_page hooks
    for fn in hooks.get_hooks("after_edit_page"):
        result = fn(request, page)
        if hasattr(result, "status_code"):
            return result

    return None


def update_action_menu(menu_items: list[ActionMenuItem], request: HttpRequest, context: Mapping) -> list:
    """Modifies the action menu items depending on the page state.

    - if the page is in a bundle that is ready to be published, remove all actions regardless of permissions
    - when the page is in a workflow task (In Preview or Ready to Publish), it is locked for editing,
      so inject the task actions (Unlock editing, Approve, Publish)
    - hide the "approve" tasks for the last editor
    - and finally tidy up the "approve" labels
    """
    updated_menu_items = menu_items
    page: Page = context["page"]
    if in_bundle_ready_to_be_published(page):
        # start with a fully locked action menu when in a bundle that is ready to be published,
        # as we want to prevent all actions.
        return [PageLockedMenuItem()]

    if is_page_in_workflow(page):
        # Both GroupReviewTask and ReadyToPublishGroupTask lock the page via locked_for_user=True.
        # This means Wagtail won't add the task's workflow actions to the menu automatically,
        # so we inject them here.
        for name, label, launch_modal in page.current_workflow_task.get_actions(page, request.user):
            icon_name = "success" if name in ["approve", "locked-approve"] else "edit"
            updated_menu_items.append(WorkflowMenuItem(name, label, launch_modal, icon_name=icon_name))

    # Do a final relabel for the "approve" actions to prevent any inconsistencies.
    final_menu_items = []
    for item in updated_menu_items:
        match item.name:
            case "action-restart-workflow":
                continue

            case "action-submit":
                # the submit/resubmit action menu item does the re-label in get_context_data, so we use our class
                final_menu_items.append(SubmitForModerationMenuItem())

            case "approve" | "locked-approve":
                item.label = get_final_approve_label(page, item.label)
                final_menu_items.append(item)

            case _:
                final_menu_items.append(item)

    return final_menu_items


@hooks.register("construct_page_action_menu")
def amend_page_action_menu_items(menu_items: list[ActionMenuItem], request: HttpRequest, context: Mapping) -> None:
    if not (context["view"] == "edit" and context.get("page")):
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
def before_edit_page_post_workflow_action_without_workflow(request: HttpRequest, page: Page) -> HttpResponse | None:
    # Prevent errors when the workflow is cancelled by someone else, just before a user submits a workflow action
    # TODO: remove when https://github.com/wagtail/wagtail/issues/13856 is fixed
    if (
        request.method == "POST"
        and request.POST.get("action-workflow-action") == "true"
        and not page.current_workflow_task
    ):
        messages.error(request, "Could not perform the action as the page is no longer in a workflow.")
        return redirect("wagtailadmin_pages:edit", page.pk, preserve_request=False)
    return None


@hooks.register("before_edit_page")
def before_edit_page(request: HttpRequest, page: Page) -> HttpResponse | None:
    if request.method != "POST":
        return None

    if in_active_bundle(page) and (
        (request.POST.get("go_live_at") and not page.go_live_at)
        or (request.POST.get("expire_at") and not page.expire_at)
    ):
        messages.error(request, "Cannot set page-level schedule while the page is in a bundle.")
        return redirect("wagtailadmin_pages:edit", page.pk, preserve_request=False)

    if request.POST.get("action-workflow-action") == "true":
        action_name = request.POST.get("workflow-action-name", "")

        # Self-approval prevention: the last editor cannot approve their own work.
        # Note: "reject" (Unlock editing) IS allowed for the last editor — they can pull their own
        # page back to draft. Only "approve" is blocked.
        if action_name == "approve" and page.latest_revision and page.latest_revision.user_id == request.user.pk:
            messages.error(
                request, "You cannot approve your own changes. Please ask another Publishing team member to do so."
            )
            return redirect("wagtailadmin_pages:edit", page.pk, preserve_request=False)

        # All workflow actions on locked pages must be intercepted here because Wagtail's edit view
        # rejects POSTs when locked_for_user is True. Both our tasks lock the page for everyone.
        if action_name in ("reject", "approve", "locked-approve") and is_page_in_workflow(page):
            # Additional guard: locked-approve only valid at Ready to Publish and not in a bundle
            if action_name == "locked-approve" and (not is_page_ready_to_publish(page) or in_active_bundle(page)):
                messages.error(request, "Cannot publish from this state.")
                return redirect("wagtailadmin_pages:edit", page.pk, preserve_request=False)

            hook_response = _perform_workflow_action_on_locked_page(request, page, action_name)
            if hook_response:
                return hook_response

            # Show appropriate success message and redirect
            if action_name == "reject":
                messages.success(request, f"Page '{page.get_admin_display_title()}' editing has been unlocked.")
                return redirect("wagtailadmin_pages:edit", page.pk, preserve_request=False)

            if action_name == "locked-approve":
                if page.go_live_at and page.go_live_at > timezone.now():
                    message = f"Page '{page.get_admin_display_title()}' has been scheduled for publishing."
                else:
                    message = f"Page '{page.get_admin_display_title()}' has been published."

                buttons = []
                if (page_url := page.get_url(request=request)) is not None:
                    buttons.append(messages.button(page_url, "View live", new_window=False))
                buttons.append(messages.button(reverse("wagtailadmin_pages:edit", args=(page.pk,)), "Edit"))
                messages.success(request, message, buttons=buttons)
                return redirect("wagtailadmin_explore", page.get_parent().pk, preserve_request=False)

            # action_name == "approve" (moving from In Preview → Ready to Publish)
            messages.success(request, f"Page '{page.get_admin_display_title()}' has been approved.")
            return redirect("wagtailadmin_pages:edit", page.pk, preserve_request=False)

    return None


@hooks.register("insert_editor_js")
def insert_workflow_tweaks_js() -> str:
    return format_html('<script src="{}"></script>', static("js/workflow-tweaks.js"))


@hooks.register("register_permissions")
def register_unlock_workflow_tasks_permission() -> QuerySet[Permission]:
    """Register the 'Unlock any workflow tasks' permission so it shows in the UI."""
    return Permission.objects.filter(content_type__app_label="wagtailadmin", codename="unlock_workflow_tasks")


@hooks.register("register_admin_urls")
def register_admin_urls() -> list[URLPattern | URLResolver]:
    """Registers the admin urls for custom workflow actions.

    @see https://docs.wagtail.org/en/stable/reference/hooks.html#register-admin-urls.
    """
    return [path("workflows/", include(admin_urls))]
