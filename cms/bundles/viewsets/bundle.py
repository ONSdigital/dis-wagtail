import logging
import textwrap
import time
from typing import TYPE_CHECKING, Any, ClassVar, Optional, cast

from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import F
from django.http import HttpRequest
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.html import format_html, format_html_join
from wagtail.admin import messages
from wagtail.admin.ui.tables import Column, DateColumn
from wagtail.admin.views.generic import CreateView, DeleteView, EditView, IndexView, InspectView
from wagtail.admin.viewsets.model import ModelViewSet
from wagtail.admin.widgets import HeaderButton, ListingButton
from wagtail.log_actions import log
from wagtail.models import Page

from cms.bundles.action_menu import BundleActionMenu
from cms.bundles.clients.api import BundleAPIClient, BundleAPIClientError, BundleAPIClientError404
from cms.bundles.decorators import datasets_bundle_api_enabled
from cms.bundles.enums import BundleContentItemState, BundleStatus
from cms.bundles.models import Bundle
from cms.bundles.notifications.slack import (
    notify_slack_of_status_change,
)
from cms.bundles.permissions import user_can_manage_bundles, user_can_preview_bundle
from cms.bundles.utils import get_data_admin_action_url, publish_bundle
from cms.core.custom_date_format import ons_date_format
from cms.datasets.models import Dataset
from cms.teams.models import Team

if TYPE_CHECKING:
    from django.db.models.fields import Field
    from django.forms import BaseForm
    from django.http import HttpResponseBase
    from django.template.response import TemplateResponse
    from django.utils.safestring import SafeString

    from cms.bundles.forms import BundleAdminForm
    from cms.bundles.models import BundlesQuerySet

logger = logging.getLogger(__name__)

# Fallback value for missing dataset metadata
MISSING_VALUE = "Data missing"


def add_exception_cause_to_form(exception: Exception, *, form: "BaseForm") -> None:
    """Adds errors from a BundleAPIClientError exception cause to the form errors."""
    cause = getattr(exception, "__cause__", None)
    if not cause:
        return

    # Currently only handle BundleAPIClientError causes
    if not isinstance(cause, BundleAPIClientError):
        return

    for error in cause.errors:
        desc = error.get("description") or "Unknown API Error"
        form.add_error(
            field=None,
            error=textwrap.shorten(desc, width=250, placeholder="..."),  # limit chars to avoid overly long errors
        )


class BundleCreateView(CreateView):
    """The Bundle create view class."""

    template_name = "bundles/wagtailadmin/edit.html"

    def get_form_kwargs(self) -> dict:
        kwargs: dict = super().get_form_kwargs()
        kwargs["access_token"] = self.request.COOKIES.get(settings.ACCESS_TOKEN_COOKIE_NAME)
        return kwargs

    def form_valid(self, form: "BundleAdminForm") -> "HttpResponseBase":
        self.form = form  # pylint: disable=attribute-defined-outside-init
        try:
            with transaction.atomic():
                self.object = self.save_instance()  # pylint: disable=attribute-defined-outside-init
        except Exception as e:  # pylint: disable=broad-exception-caught
            error = getattr(e, "message", str(e))
            error_message = f"{self.get_error_message()} {error}."
            add_exception_cause_to_form(e, form=form)
            messages.validation_error(self.request, error_message, form)
            error_response: HttpResponseBase = self.render_to_response(self.get_context_data(form=form))
            return error_response

        response: HttpResponseBase = self.save_action()

        hook_response: Optional[HttpResponseBase] = self.run_after_hook()
        if hook_response is not None:
            return hook_response

        return response

    def save_instance(self) -> Bundle:
        """Automatically set the creating user on Bundle creation."""
        instance: Bundle = super().save_instance()
        instance.created_by = self.request.user
        instance.save(update_fields=["created_by"])
        return instance

    def get_success_url(self) -> str:
        return cast(str, self.get_edit_url())

    def get_success_message(self, instance: Bundle) -> str:
        return "Bundle successfully created."

    def get_success_buttons(self) -> list:
        return []

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context: dict[str, Any] = super().get_context_data(**kwargs)

        # initialise the action menu
        action_menu = BundleActionMenu(self.request, bundle=None)
        context["media"] += action_menu.media
        context["action_menu"] = action_menu
        return context


class BundleEditView(EditView):
    """The Bundle edit view class."""

    template_name = "bundles/wagtailadmin/edit.html"
    has_content_changes: bool = False
    start_time: float | None = None

    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> "HttpResponseBase":
        if (instance := self.get_object()) and instance.status == BundleStatus.PUBLISHED:
            return redirect(self.index_url_name)

        if request.method == "POST" and self.get_action(request) not in self.get_available_actions():
            # someone's trying to POST with an action that is not available, so bail out early
            raise PermissionDenied

        response: HttpResponseBase = super().dispatch(request, *args, **kwargs)
        return response

    def get_form_kwargs(self) -> dict:
        kwargs: dict = super().get_form_kwargs()
        kwargs["access_token"] = self.request.COOKIES.get(settings.ACCESS_TOKEN_COOKIE_NAME)

        if self.request.method == "POST":
            data = self.request.POST.copy()
            if "action-save-to-preview" in self.request.POST:
                data["status"] = BundleStatus.IN_REVIEW.value
            elif "action-approve" in self.request.POST:
                data["status"] = BundleStatus.APPROVED.value
                data["approved_at"] = timezone.now()
                data["approved_by"] = self.request.user
            elif "action-return-to-draft" in self.request.POST:
                data["status"] = BundleStatus.DRAFT.value
            elif "action-return-to-preview" in self.request.POST:
                data["status"] = BundleStatus.IN_REVIEW.value
            elif "action-publish" in self.request.POST:
                data["status"] = BundleStatus.PUBLISHED.value
            else:
                data["status"] = self.get_object().status

            kwargs["data"] = data
        return kwargs

    def form_valid(self, form: "BundleAdminForm") -> "HttpResponseBase":
        self.form = form  # pylint: disable=attribute-defined-outside-init
        try:
            with transaction.atomic():
                self.object = self.save_instance()  # pylint: disable=attribute-defined-outside-init
        except Exception as e:  # pylint: disable=broad-exception-caught
            error = getattr(e, "message", str(e))
            error_message = f"{self.get_error_message()} {error}."
            add_exception_cause_to_form(e, form=form)
            messages.validation_error(self.request, error_message, form)
            error_response: HttpResponseBase = self.render_to_response(self.get_context_data(form=form))
            return error_response

        response: HttpResponseBase = self.save_action()

        hook_response: Optional[HttpResponseBase] = self.run_after_hook()
        if hook_response is not None:
            return hook_response

        return response

    def save_instance(self) -> Bundle:
        # Capture before state for comparison
        original_state = {
            "teams": set(self.object.teams.values_list("team_id", flat=True)),
            "pages": set(self.object.bundled_pages.values_list("page_id", flat=True)),
            "datasets": set(self.object.bundled_datasets.values_list("dataset_id", flat=True)),
            "pub_date": self.object.publication_date,
        }

        instance: Bundle = self.form.save()
        self.has_content_changes = self.form.has_changed()

        if not self.has_content_changes:
            return instance

        log(action="wagtail.edit", instance=instance, content_changed=True, data={"fields": self.form.changed_data})

        # Log content changes
        self._log_content_changes(instance, original_state)

        if "status" not in self.form.changed_data:
            return instance

        kwargs: dict = {"content_changed": self.has_content_changes}
        original_status = BundleStatus[self.form.original_status].label
        url = self.request.build_absolute_uri(instance.full_inspect_url)

        if instance.status == BundleStatus.APPROVED:
            action = "bundles.approve"
            kwargs["data"] = {"old": original_status}
            notify_slack_of_status_change(instance, original_status, user=self.request.user, url=url)
        elif instance.status == BundleStatus.PUBLISHED.value:
            action = "wagtail.publish"
            self.start_time = time.time()
        else:
            action = "bundles.update_status"
            kwargs["data"] = {
                "old": original_status,
                "new": instance.get_status_display(),
            }
            notify_slack_of_status_change(instance, original_status, user=self.request.user, url=url)

        # now log the status change
        log(
            action=action,
            instance=instance,
            **kwargs,
        )

        return instance

    def _log_content_changes(self, instance: Bundle, original_state: dict[str, Any]) -> None:
        """Log changes to bundle content (teams, pages, datasets, schedule)."""
        self._log_team_changes(instance, original_state["teams"])
        self._log_page_changes(instance, original_state["pages"])
        self._log_dataset_changes(instance, original_state["datasets"])
        self._log_schedule_changes(instance, original_state["pub_date"])

    def _log_team_changes(self, instance: Bundle, original_teams: set[int]) -> None:
        """Log team additions and removals."""
        new_teams = set(instance.teams.values_list("team_id", flat=True))
        added = new_teams - original_teams
        removed = original_teams - new_teams

        for team_id in added:
            team = Team.objects.get(id=team_id)
            log(action="bundles.team_added", instance=instance, data={"team_name": team.name})

        for team_id in removed:
            team = Team.objects.get(id=team_id)
            log(action="bundles.team_removed", instance=instance, data={"team_name": team.name})

    def _log_page_changes(self, instance: Bundle, original_pages: set[int]) -> None:
        """Log page additions and removals."""
        new_pages = set(instance.bundled_pages.values_list("page_id", flat=True))
        added = new_pages - original_pages
        removed = original_pages - new_pages

        for page_id in added:
            page = Page.objects.get(id=page_id)
            log(action="bundles.page_added", instance=instance, data={"page_title": page.title})

        for page_id in removed:
            page = Page.objects.get(id=page_id)
            log(action="bundles.page_removed", instance=instance, data={"page_title": page.title})

    def _log_dataset_changes(self, instance: Bundle, original_datasets: set[int]) -> None:
        """Log dataset additions and removals."""
        new_datasets = set(instance.bundled_datasets.values_list("dataset_id", flat=True))
        added = new_datasets - original_datasets
        removed = original_datasets - new_datasets

        for dataset_id in added:
            dataset = Dataset.objects.get(id=dataset_id)
            log(action="bundles.dataset_added", instance=instance, data={"dataset_title": dataset.title})

        for dataset_id in removed:
            dataset = Dataset.objects.get(id=dataset_id)
            log(action="bundles.dataset_removed", instance=instance, data={"dataset_title": dataset.title})

    def _log_schedule_changes(self, instance: Bundle, original_pub_date: Any) -> None:
        """Log publication date changes."""
        if instance.publication_date != original_pub_date:
            old_date = original_pub_date.strftime("%Y-%m-%d %H:%M") if original_pub_date else "Not set"
            new_date = instance.publication_date.strftime("%Y-%m-%d %H:%M") if instance.publication_date else "Not set"
            log(action="bundles.schedule_changed", instance=instance, data={"old": old_date, "new": new_date})

    def run_after_hook(self) -> Optional["HttpResponseBase"]:
        """This method allows calling hooks or additional logic after an action has been executed.

        In our case, we want to replicate the scheduled publication (send Slack notification, publish pages, update RC).
        """
        if self.action == "publish" or (self.action == "edit" and self.object.status == BundleStatus.PUBLISHED):
            publish_bundle(self.object, update_status=False)

    def get_action(self, request: "HttpRequest") -> str:
        """Determine the POST action."""
        for action in self.get_available_actions():
            if request.POST.get(f"action-{action}"):
                return action
        # EditView.get_action falls back to "edit". We want to prevent that in order to enforce
        # the available actions depending on the bundle status
        return "invalid"

    def get_available_actions(self) -> list[str]:
        """Determines the valid actions for the edit form depending on the bundle state."""
        bundle = self.get_object()

        match bundle.status:
            case BundleStatus.DRAFT:
                return ["edit", "save-to-preview"]
            case BundleStatus.IN_REVIEW:
                return ["edit", "return-to-draft", "approve"]
            case BundleStatus.APPROVED:
                actions = ["return-to-draft", "return-to-preview"]
                if bundle.can_be_manually_published:
                    actions += ["publish"]
                return actions
            case _:
                return []

    def get_success_url(self) -> str:
        match self.object.status:
            case BundleStatus.IN_REVIEW:
                url = self.get_edit_url() if "action-edit" in self.request.POST else self.get_inspect_url()
            case BundleStatus.APPROVED:
                url = self.get_inspect_url()
            case BundleStatus.PUBLISHED:
                url = reverse(self.index_url_name)
            case _:
                url = self.get_edit_url()
        return cast(str, url)

    def get_success_buttons(self) -> list:
        # only include the edit button when not staying on the edit page.
        if "action-edit" in self.request.POST:
            return []

        if self.object.status in [BundleStatus.IN_REVIEW, BundleStatus.APPROVED]:
            return cast(list, super().get_success_buttons())

        return []

    def get_context_data(self, **kwargs: Any) -> dict:
        """Updates the template context.

        Show the "save and approve" button if the bundle has the right status, and we have a different user
        than the creator
        """
        context: dict = super().get_context_data(**kwargs)

        # initialise the action menu
        action_menu = BundleActionMenu(self.request, bundle=self.get_object())
        context["media"] += action_menu.media
        context["action_menu"] = action_menu

        return context


class BundleInspectView(InspectView):
    """The Bundle inspect view class."""

    template_name = "bundles/wagtailadmin/inspect.html"

    def dispatch(self, request: "HttpRequest", *args: Any, **kwargs: Any) -> "TemplateResponse":
        if not user_can_preview_bundle(self.request.user, self.object):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)  # type: ignore[no-any-return]

    @cached_property
    def can_manage(self) -> bool:
        return user_can_manage_bundles(self.request.user)

    def get_fields(self) -> list[str]:
        """Returns the list of fields to include in the inspect view.

        Note: values are inserted by methods following the get_FIELDNAME_display_value pattern.
        See InspectView.get_field_display_value.
        """
        if self.can_manage:
            return [
                "name",
                "bundle_api_bundle_id",
                "status",
                "created_at",
                "created_by",
                "approved",
                "scheduled_publication",
                "release_calendar_page",
                "teams",
                "pages",
                "bundled_datasets",
            ]

        return [
            "name",
            "created_at",
            "created_by",
            "scheduled_publication",
            "release_calendar_page",
            "pages",
            "bundled_datasets",
        ]

    def get_field_label(self, field_name: str, field: "Field") -> str:
        match field_name:
            case "approved":
                label = "Approval status"
            case "scheduled_publication":
                label = "Scheduled publication"
            case "pages":
                label = "Pages"
            case "bundled_datasets":
                label = "Datasets"
            case "release_calendar_page":
                label = "Associated release calendar page"
            case "bundle_api_bundle_id":
                value = self.get_field_display_value(field_name, field)
                label = "Dataset Bundle API ID" if value else ""
            case _:
                label = super().get_field_label(field_name, field)

        return label

    def get_created_at_display_value(self) -> str:
        return ons_date_format(self.object.created_at, settings.DATETIME_FORMAT)

    def get_approved_at_display_value(self) -> str:
        return ons_date_format(self.object.approved_at, settings.DATETIME_FORMAT) if self.object.approved_at else ""

    def get_approved_display_value(self) -> str:
        """Custom approved by formatting. Varies based on status, and approver/time of approval."""
        if self.object.status in [BundleStatus.APPROVED, BundleStatus.PUBLISHED]:
            if self.object.approved_by_id and self.object.approved_at:
                return (
                    f"{self.object.approved_by} on {ons_date_format(self.object.approved_at, settings.DATETIME_FORMAT)}"
                )
            return "Unknown approval data"
        return "Pending approval"

    def get_scheduled_publication_display_value(self) -> str:
        """Displays the scheduled publication date, if set."""
        if self.object.scheduled_publication_date:
            return ons_date_format(self.object.scheduled_publication_date, settings.DATETIME_FORMAT)
        return "No scheduled publication"

    def get_release_calendar_page_display_value(self) -> str:
        """Returns the release calendar page link if it exists."""
        if self.object.release_calendar_page:
            if self.object.status == BundleStatus.PUBLISHED:
                url = self.object.release_calendar_page.get_url(request=self.request)
            else:
                url = reverse("bundles:preview_release_calendar", args=[self.object.pk])

            return format_html(
                '<a href="{}" target="_blank" rel="noopener">{}</a>',
                url,
                self.object.release_calendar_page.get_admin_display_title(),
            )
        return "N/A"

    def get_pages_for_manager(self) -> "SafeString":
        """Returns all the bundle pages.
        Publishing Admins / Officers can see everything when inspecting the bundle.
        """
        pages = self.object.get_bundled_pages().specific().defer_streamfields()

        def get_page_status(page: "Page") -> str:
            if self.object.status == BundleStatus.PUBLISHED and page.live:
                return "Published"
            return page.current_workflow_state.current_task_state.task.name if page.current_workflow_state else "Draft"

        def get_action(page: "Page") -> str:
            if self.object.status == BundleStatus.PUBLISHED and page.live:
                return str(page.get_url(request=self.request))
            return reverse(
                "bundles:preview",
                args=(
                    self.object.pk,
                    page.pk,
                ),
            )

        data = (
            (
                reverse("wagtailadmin_pages:edit", args=[page.pk]),
                page.get_admin_display_title(),
                page.get_verbose_name(),
                get_page_status(page),
                get_action(page),
            )
            for page in pages
        )

        page_data = format_html_join(
            "\n",
            '<tr><td class="title"><strong><a href="{}">{}</a></strong></td><td>{}</td><td>{}</td> '
            '<td><a href="{}" class="button button-small button-secondary">Preview</a></td></tr>',
            data,
        )

        return format_html(
            "<table class='listing'><thead><tr><th>Title</th><th>Type</th>"
            "<th>Status</th><th>Actions</th></tr></thead>{}</table>",
            page_data,
        )

    def get_pages_for_previewer(self) -> "SafeString":
        """Returns the list of bundle pages a previewer-only user can see when inspecting the bundle.
        These are pages in the bundle that are in the "Ready for review" workflow state.
        """
        pages = self.object.get_pages_for_previewers()

        data = (
            (
                page.get_admin_display_title(),
                page.get_verbose_name(),
                reverse(
                    "bundles:preview",
                    args=(
                        self.object.pk,
                        page.pk,
                    ),
                ),
            )
            for page in pages
        )

        page_data = format_html_join(
            "\n",
            '<tr><td class="title"><strong>{}</strong></td><td>{}</td> '
            '<td><a href="{}" class="button button-small button-secondary">Preview</a></td></tr>',
            data,
        )

        return format_html(
            "<table class='listing'><thead><tr><th>Title</th><th>Type</th><th>Actions</th></tr></thead>{}</table>",
            page_data,
        )

    def get_pages_display_value(self) -> "SafeString | str":
        """Returns formatted markup for Pages linked to the Bundle."""
        if self.can_manage:
            return self.get_pages_for_manager()

        if user_can_preview_bundle(self.request.user, self.object):
            return self.get_pages_for_previewer()

        return ""

    def get_teams_display_value(self) -> str:
        value: str = self.object.get_teams_display()
        return value

    def get_bundle_api_bundle_id_display_value(self) -> str:
        value: str = self.object.bundle_api_bundle_id
        return value

    @staticmethod
    def get_human_readable_state(state: str) -> str:
        """Converts a machine-readable state string to a human-readable format."""
        if not state or state == MISSING_VALUE:
            return MISSING_VALUE
        match state:
            case BundleContentItemState.APPROVED:
                return "Approved"
            case BundleContentItemState.PUBLISHED:
                return "Published"
            case _:
                return state.replace("_", " ").title()

    def _get_api_items_by_content_id(self) -> dict[str, dict[str, Any]]:
        """Fetch Bundle API contents and build a lookup dict by content_id."""
        client = BundleAPIClient(access_token=self.request.COOKIES.get(settings.ACCESS_TOKEN_COOKIE_NAME))
        bundle_contents = client.get_bundle_contents(self.object.bundle_api_bundle_id)

        api_items: dict[str, dict[str, Any]] = {}
        for content_item in bundle_contents.get("items", []):
            if content_item.get("content_type") == "DATASET" and (content_id := content_item.get("id")):
                api_items[content_id] = content_item
        return api_items

    @staticmethod
    def _extract_api_fields(api_item: dict[str, Any] | None) -> tuple[str, str, str | None]:
        """Extract state, edit_url, and preview_url from API item.

        Returns:
            Tuple of (state, edit_url, preview_url)
        """
        if not api_item:
            return "", "#", None

        links = api_item.get("links", {})
        return (
            api_item.get("state", ""),
            links.get("edit") or "#",
            links.get("preview"),
        )

    def _build_action_button(self, state: str, preview_url: str | None, dataset: "Dataset") -> "SafeString | str":
        """Build the action button HTML based on dataset state."""
        if state == BundleContentItemState.PUBLISHED:
            view_url = get_data_admin_action_url("preview", dataset.namespace, dataset.edition, str(dataset.version))
            return format_html(
                '<a href="{}" class="button button-small button-secondary">View Live</a>',
                view_url,
            )
        if preview_url:
            cms_preview_url = reverse(
                "bundles:preview_dataset",
                args=[self.object.pk, dataset.namespace, dataset.edition, dataset.version],
            )
            return format_html(
                '<a href="{}" class="button button-small button-secondary">Preview</a>',
                cms_preview_url,
            )
        return ""

    def _get_processed_datasets(self) -> list[dict[str, "SafeString | str"]]:
        """Processes dataset information by hydrating local DB records with API data.

        Uses local database records as the source of truth, then enriches them with
        state and edit URL information from the Bundle API.
        """
        try:
            api_items_by_content_id = self._get_api_items_by_content_id()
        except BundleAPIClientError:
            api_items_by_content_id = {}

        processed_data = []
        for bundled_dataset in self.object.bundled_datasets.select_related("dataset").all():
            if not bundled_dataset.dataset:
                continue

            dataset = bundled_dataset.dataset
            api_item = api_items_by_content_id.get(bundled_dataset.bundle_api_content_id)
            state, edit_url, preview_url = self._extract_api_fields(api_item)

            item: dict[str, SafeString | str] = {
                "title": dataset.title,
                "edition": dataset.formatted_edition or MISSING_VALUE,
                "version": str(dataset.version) if dataset.version else MISSING_VALUE,
                "state": self.get_human_readable_state(state),
                "action_button": self._build_action_button(state, preview_url, dataset),
                "edit_url": edit_url,
            }

            processed_data.append(item)

        return processed_data

    def _render_datasets_table(self, include_edit_links: bool) -> "SafeString | str":
        """Renders datasets as an HTML table.

        Args:
            include_edit_links: If True, titles are hyperlinked to data admin.
                            If False, titles are plain text.
        """
        processed_datasets = self._get_processed_datasets()

        if not processed_datasets:
            return "No datasets in bundle"

        row_html_list: list[SafeString] = []
        for item in processed_datasets:
            if include_edit_links:
                title_col = format_html(
                    '<td class="title"><strong><a href="{}">{}</a></strong></td>',
                    item["edit_url"],
                    item["title"],
                )
            else:
                title_col = format_html('<td class="title"><strong>{}</strong></td>', item["title"])

            other_cols = format_html(
                "<td>{}</td><td>{}</td><td>{}</td><td>{}</td>",
                item["edition"],
                item["version"],
                item["state"],
                item["action_button"],
            )

            row_html_list.append(format_html("<tr>{}{}</tr>", title_col, other_cols))

        dataset_data = format_html_join("\n", "{}", ((row,) for row in row_html_list))

        return format_html(
            "<table class='listing'>"
            "<thead><tr><th>Title</th><th>Edition</th><th>Version</th><th>State</th><th>Actions</th></tr></thead>"
            "<tbody>{}</tbody>"
            "</table>",
            dataset_data,
        )

    def get_datasets_for_manager(self) -> "SafeString | str":
        """Returns all the bundle datasets for managers with edit links."""
        return self._render_datasets_table(include_edit_links=True)

    def get_datasets_for_viewer(self) -> "SafeString | str":
        """Returns all the bundle datasets for viewers without edit links."""
        return self._render_datasets_table(include_edit_links=False)

    def get_bundled_datasets_display_value(self) -> "SafeString | str":
        """Returns formatted markup for datasets linked to the Bundle."""
        if not self.object.has_datasets:
            return "No datasets in bundle"

        if not self.object.bundle_api_bundle_id:
            return "Unable to use the Dataset API to display datasets."

        if self.can_manage:
            return self.get_datasets_for_manager()

        return self.get_datasets_for_viewer()


class BundleDeleteView(DeleteView):
    has_errors = False

    @datasets_bundle_api_enabled
    def sync_bundle_deletion_with_bundle_api(self, instance: Bundle) -> None:
        """Syncs the deletion of the Bundle in the CMS with the Bundle API by deleting the corresponding Bundle API
        bundle.
        """
        if not instance.bundle_api_bundle_id:
            return

        access_token = self.request.COOKIES.get(settings.ACCESS_TOKEN_COOKIE_NAME)
        client = BundleAPIClient(access_token=access_token)

        try:
            client.delete_bundle(instance.bundle_api_bundle_id)
        except BundleAPIClientError404:
            logger.warning(
                "Bundle not found in Bundle API when deleting CMS bundle",
                extra={"id": instance.pk, "api_id": instance.bundle_api_bundle_id},
            )
            # No need to save fields or raise an error as we are about to delete the CMS bundle anyway
        except BundleAPIClientError as e:
            msg = "Failed to delete bundle from Bundle API"
            logger.exception(msg, extra={"id": instance.pk, "api_id": instance.bundle_api_bundle_id})
            raise ValidationError(msg) from e

    def delete_action(self) -> None:
        with transaction.atomic():
            bundle = self.object
            log(instance=self.object, action="wagtail.delete")
            self.object.delete()
            self.sync_bundle_deletion_with_bundle_api(bundle)

    def form_valid(self, form: "BundleAdminForm") -> "HttpResponseBase":
        try:
            response: HttpResponseBase = super().form_valid(form)
            return response
        except ValidationError as e:
            error = getattr(e, "message", str(e))
            error_message = f"The bundle could not be deleted due to errors. {error}."
            messages.error(self.request, error_message)
            return redirect(reverse(self.index_url_name))


class BundleIndexView(IndexView):
    """The Bundle index view class.

    We adjust the queryset and change the edit URL based on the bundle status.
    """

    model = Bundle
    default_ordering = "name"

    def get_base_queryset(self) -> "BundlesQuerySet":
        """Modifies the Bundle queryset to vary results based on the user capabilities."""
        queryset: BundlesQuerySet = super().get_base_queryset()

        if not self.can_manage:
            queryset = queryset.previewable().filter(teams__team__in=self.request.user.active_team_ids).distinct()

        return queryset

    def filter_queryset(self, queryset: "BundlesQuerySet") -> "BundlesQuerySet":
        # automatically filter out published bundles if the status filter is not applied
        if not self.request.GET.get("status"):
            queryset = queryset.exclude(status=BundleStatus.PUBLISHED)

        return cast("BundlesQuerySet", super().filter_queryset(queryset))

    def order_queryset(self, queryset: "BundlesQuerySet") -> "BundlesQuerySet":
        if self.ordering in ["status", "-status", "scheduled_publication_date", "-scheduled_publication_date"]:
            match self.ordering:
                case "scheduled_publication_date":
                    return queryset.annotate_release_date().order_by(F("release_date").asc(nulls_last=True))
                case "-scheduled_publication_date":
                    return queryset.annotate_release_date().order_by(F("release_date").desc(nulls_last=True))
                case "status":
                    return queryset.annotate_status_label().order_by(F("status_label").asc())
                case "-status":
                    return queryset.annotate_status_label().order_by(F("status_label").desc())

        return cast("BundlesQuerySet", super().order_queryset(queryset))

    def get_edit_url(self, instance: Bundle) -> str | None:
        """Override the default edit url to disable the edit URL for released bundles."""
        if instance.status != BundleStatus.PUBLISHED:
            edit_url: str | None = super().get_edit_url(instance)
            return edit_url
        return None

    def get_copy_url(self, instance: Bundle) -> str | None:
        """Disables the bundle copy."""
        return None

    @cached_property
    def can_manage(self) -> bool:
        return user_can_manage_bundles(self.request.user)

    def get_header_buttons(self) -> list[HeaderButton]:
        if not self.can_manage:
            return []

        buttons = self.header_buttons
        filtered_url = f"{self.get_index_url()}?status={BundleStatus.APPROVED}"
        buttons.append(
            HeaderButton(
                label='View "Ready to publish"',
                url=filtered_url,
                icon_name="check",
                attrs={
                    "data-controller": "w-tooltip",
                    "data-w-tooltip-content-value": "View bundles that are ready to publish",
                    "aria-label": "View bundles that are ready to publish",
                },
            )
        )

        return sorted(buttons)

    def get_list_buttons(self, instance: Bundle) -> list[ListingButton]:
        buttons = []
        if edit_url := self.get_edit_url(instance):
            buttons.append(
                ListingButton(
                    "Edit",
                    url=edit_url,
                    icon_name="edit",
                    attrs={"aria-label": f"Edit '{instance!s}'"},
                    priority=10,
                )
            )
        if inspect_url := self.get_inspect_url(instance):
            buttons.append(
                ListingButton(
                    "Inspect",
                    url=inspect_url,
                    icon_name="info-circle",
                    attrs={"aria-label": f"Inspect '{instance!s}'"},
                    priority=20,
                )
            )
        return buttons

    @cached_property
    def columns(self) -> list[Column]:
        """Defines the list of desired columns in the listing."""
        return [
            self._get_title_column("name"),
            Column("scheduled_publication_date", label="Scheduled for", sort_key="scheduled_publication_date"),
            Column("get_status_display", label="Status", sort_key="status"),
            DateColumn(name="updated_at", sort_key="updated_at"),
        ]


class BundleViewSet(ModelViewSet):
    """The viewset class for Bundle.

    We extend the generic ModelViewSet to add our customisations.
    @see https://docs.wagtail.org/en/stable/reference/viewsets.html#modelviewset
    """

    model = Bundle
    icon = "boxes-stacked"
    add_view_class = BundleCreateView
    edit_view_class = BundleEditView
    delete_view_class = BundleDeleteView
    inspect_view_class = BundleInspectView
    index_view_class = BundleIndexView
    list_filter: ClassVar[list[str]] = ["status", "created_by"]
    add_to_admin_menu = True
    inspect_view_enabled = True
    menu_order = 150


bundle_viewset = BundleViewSet("bundle")
