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
from .action_menu import ReturnToDraftMenuItem, SubmitForModerationMenuItem
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


def update_action_menu(menu_items: list[ActionMenuItem], request: HttpRequest, context: Mapping) -> list:
    """Modifies the action menu items depending on the page state.

    - if the page is in a bundle that is ready to be published, remove all actions regardless of permissions
    - when the page is in a workflow task (In Preview or Ready to Publish), it is locked for editing,
      so inject the task actions (Approve, Publish) and the 'Return to draft' link
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

        # Inject workflow actions (approve, locked-approve)
        for name, label, launch_modal in page.current_workflow_task.get_actions(page, request.user):
            icon_name = "success" if name in ["approve", "locked-approve"] else "edit"
            updated_menu_items.append(WorkflowMenuItem(name, label, launch_modal, icon_name=icon_name))

        # Inject 'Return to draft' link (available to anyone who can access the editor)
        if page.current_workflow_task.user_can_access_editor(page, request.user):
            url = reverse("workflows:unlock", args=(page.pk,))
            updated_menu_items.append(
                ReturnToDraftMenuItem("return-to-draft", "Return to draft", icon_name="draft", item_url=url)
            )

    # Do a final relabel for the "approve" actions to prevent any inconsistencies.
    final_menu_items = []
    for item in updated_menu_items:
        match item.name:
            case "action-restart-workflow":
                continue

            case "action-cancel-workflow":
                # Hide the default cancel workflow item — we use our own 'Return to draft' view instead
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
        if action_name == "approve" and page.latest_revision and page.latest_revision.user_id == request.user.pk:
            messages.error(
                request, "You cannot approve your own changes. Please ask another Publishing team member to do so."
            )
            return redirect("wagtailadmin_pages:edit", page.pk, preserve_request=False)

        # Handle 'approve' on the GroupReviewTask (In Preview) — page is locked so Wagtail
        # won't reach perform_workflow_action. We intercept and perform it without saving the form.
        if action_name == "approve" and is_page_in_workflow(page):
            import json

            extra_workflow_data_json = request.POST.get("workflow-action-extra-data", "{}")
            extra_workflow_data = json.loads(extra_workflow_data_json)
            page.current_workflow_task.on_action(
                page.current_workflow_task_state, request.user, action_name, **extra_workflow_data
            )

            for fn in hooks.get_hooks("after_edit_page"):
                result = fn(request, page)
                if hasattr(result, "status_code"):
                    return result

            messages.success(request, f"Page '{page.get_admin_display_title()}' has been approved.")
            return redirect("wagtailadmin_pages:edit", page.pk, preserve_request=False)

        # Handle 'locked-approve' on the ReadyToPublishGroupTask — same pattern.
        if action_name == "locked-approve" and is_page_ready_to_publish(page) and not in_active_bundle(page):
            page.current_workflow_task.on_action(page.current_workflow_task_state, request.user, action_name)

            for fn in hooks.get_hooks("after_edit_page"):
                result = fn(request, page)
                if hasattr(result, "status_code"):
                    return result

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
