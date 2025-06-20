import time
from typing import TYPE_CHECKING, Any, ClassVar

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.formats import date_format
from django.utils.functional import cached_property
from django.utils.html import format_html, format_html_join
from wagtail.admin.ui.tables import Column, DateColumn, UpdatedAtColumn, UserColumn
from wagtail.admin.views.generic import CreateView, EditView, IndexView, InspectView
from wagtail.admin.viewsets.model import ModelViewSet
from wagtail.log_actions import log

from cms.bundles.enums import BundleStatus
from cms.bundles.models import Bundle
from cms.bundles.notifications import (
    notify_slack_of_publication_start,
    notify_slack_of_publish_end,
    notify_slack_of_status_change,
)
from cms.bundles.permissions import user_can_manage_bundles, user_can_preview_bundle
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

    def save_instance(self) -> Bundle:
        """Automatically set the creating user on Bundle creation."""
        instance: Bundle = super().save_instance()
        instance.created_by = self.request.user
        instance.save(update_fields=["created_by"])
        return instance


class BundleEditView(EditView):
    """The Bundle edit view class."""

    actions: ClassVar[list[str]] = ["edit", "save-and-approve", "publish", "unschedule"]
    template_name = "bundles/wagtailadmin/edit.html"
    has_content_changes: bool = False
    start_time: float | None = None

    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> "HttpResponseBase":
        if (instance := self.get_object()) and instance.status == BundleStatus.PUBLISHED:
            return redirect(self.index_url_name)

        response: HttpResponseBase = super().dispatch(request, *args, **kwargs)
        return response

    def get_form_kwargs(self) -> dict:
        kwargs: dict = super().get_form_kwargs()
        if self.request.method == "POST":
            data = self.request.POST.copy()
            if "action-save-and-approve" in self.request.POST:
                data["status"] = BundleStatus.APPROVED.value
                data["approved_at"] = timezone.now()
                data["approved_by"] = self.request.user
                kwargs["data"] = data
            elif "action-unschedule" in self.request.POST:
                data["status"] = BundleStatus.DRAFT.value
                kwargs["data"] = data
            elif "action-publish" in self.request.POST:
                data["status"] = BundleStatus.PUBLISHED.value
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
        url = self.request.build_absolute_uri(reverse("bundle:inspect", args=(instance.pk,)))

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

    def get_context_data(self, **kwargs: Any) -> dict:
        """Updates the template context.

        Show the "save and approve" button if the bundle has the right status, and we have a different user
        than the creator
        """
        context: dict = super().get_context_data(**kwargs)

        context["show_save_and_approve"] = self.object.can_be_approved
        context["show_publish"] = (
            self.object.status == BundleStatus.APPROVED and not self.object.scheduled_publication_date
        )
        context["show_unschedule"] = (
            self.object.status == BundleStatus.APPROVED and self.object.scheduled_publication_date
        )

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
        """Returns the list of fields to include in the inspect view."""
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

    def get_approved_display_value(self) -> str:
        """Custom approved by formatting. Varies based on status, and approver/time of approval."""
        if self.object.status in [BundleStatus.APPROVED, BundleStatus.PUBLISHED]:
            if self.object.approved_by_id and self.object.approved_at:
                return f"{self.object.approved_by} on {date_format(self.object.approved_at, settings.DATETIME_FORMAT)}"
            return "Unknown approval data"
        return "Pending approval"

    def get_scheduled_publication_display_value(self) -> str:
        """Displays the scheduled publication date, if set."""
        if self.object.scheduled_publication_date:
            return date_format(self.object.scheduled_publication_date, settings.DATETIME_FORMAT)
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

    def get_base_queryset(self) -> "BundlesQuerySet":
        """Modifies the Bundle queryset with the related created_by ForeignKey selected to avoid N+1 queries."""
        queryset: BundlesQuerySet = super().get_base_queryset()

        if not self.can_manage:
            queryset = queryset.previewable().filter(teams__team__in=self.request.user.active_team_ids).distinct()

        return queryset.select_related("created_by").prefetch_related("teams__team")

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

    @cached_property
    def columns(self) -> list[Column]:
        """Defines the list of desired columns in the listing."""
        if self.can_manage:
            return [
                self._get_title_column("__str__"),
                Column("scheduled_publication_date", label="Scheduled for"),
                Column("get_status_display", label="Status"),
                UpdatedAtColumn(),
                DateColumn(name="created_at", label="Added", sort_key="created_at"),
                UserColumn("created_by", label="Added by"),
                Column(name="teams", accessor="get_teams_display", label="Preview teams"),
                DateColumn(name="approved_at", label="Approved at", sort_key="approved_at"),
                UserColumn("approved_by"),
            ]

        return [
            self._get_title_column("__str__"),
            Column("scheduled_publication_date", label="Scheduled for"),
            DateColumn(name="created_at", label="Added", sort_key="created_at"),
            UserColumn("created_by", label="Added by"),
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
