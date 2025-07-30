import time
from typing import TYPE_CHECKING, Any, ClassVar, cast

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.db.models import F
from django.http import HttpRequest
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.html import format_html, format_html_join
from wagtail.admin.ui.tables import Column, DateColumn
from wagtail.admin.views.generic import CreateView, EditView, IndexView, InspectView
from wagtail.admin.viewsets.model import ModelViewSet
from wagtail.admin.widgets import HeaderButton, ListingButton
from wagtail.log_actions import log

from cms.bundles.action_menu import BundleActionMenu
from cms.bundles.enums import BundleStatus
from cms.bundles.models import Bundle
from cms.bundles.notifications.slack import (
    notify_slack_of_publication_start,
    notify_slack_of_publish_end,
    notify_slack_of_status_change,
)
from cms.bundles.permissions import user_can_manage_bundles, user_can_preview_bundle
from cms.core.custom_date_format import ons_date_format
from cms.datasets.models import Dataset

if TYPE_CHECKING:
    from django.db.models.fields import Field
    from django.http import HttpResponseBase
    from django.template.response import TemplateResponse
    from django.utils.safestring import SafeString
    from wagtail.models import Page

    from cms.bundles.models import BundlesQuerySet


class BundleCreateView(CreateView):
    """The Bundle create view class."""

    template_name = "bundles/wagtailadmin/edit.html"

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

    def save_instance(self) -> Bundle:
        instance: Bundle = self.form.save()
        self.has_content_changes = self.form.has_changed()

        if not self.has_content_changes:
            return instance

        log(action="wagtail.edit", instance=instance, content_changed=True, data={"fields": self.form.changed_data})

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

    def run_after_hook(self) -> None:
        """This method allows calling hooks or additional logic after an action has been executed.

        In our case, we want to send a Slack notification if manually published, and approve any of the
        related pages that are in a Wagtail workflow.
        """
        if self.action == "publish" or (self.action == "edit" and self.object.status == BundleStatus.PUBLISHED):
            notify_slack_of_publication_start(self.object, user=self.request.user)
            start_time = self.start_time or time.time()
            for page in self.object.get_bundled_pages():
                if page.current_workflow_state:
                    page.current_workflow_state.current_task_state.approve(user=self.request.user)

            notify_slack_of_publish_end(self.object, time.time() - start_time, user=self.request.user)

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
                return "Approval status"
            case "scheduled_publication":
                return "Scheduled publication"
            case "pages":
                return "Pages"
            case "bundled_datasets":
                return "Datasets"
            case "release_calendar_page":
                return "Associated release calendar page"
            case _:
                return super().get_field_label(field_name, field)  # type: ignore[no-any-return]

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
        """Returns all the bundle page.
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

    def get_bundled_datasets_display_value(self) -> str:
        """Returns formatted markup for datasets linked to the Bundle."""
        if self.object.bundled_datasets.exists():
            datasets = Dataset.objects.filter(pk__in=self.object.bundled_datasets.values_list("dataset__pk", flat=True))
            return format_html(
                "<ol>{}</ol>",
                format_html_join(
                    "\n",
                    '<li><a href="{}" target="_blank" rel="noopener">{}</a></li>',
                    ((bundled_dataset.website_url, bundled_dataset) for bundled_dataset in datasets),
                ),
            )
        return "No datasets in bundle"


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
    inspect_view_class = BundleInspectView
    index_view_class = BundleIndexView
    list_filter: ClassVar[list[str]] = ["status", "created_by"]
    add_to_admin_menu = True
    inspect_view_enabled = True
    menu_order = 150


bundle_viewset = BundleViewSet("bundle")
