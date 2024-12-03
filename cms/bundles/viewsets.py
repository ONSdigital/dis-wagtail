import time
from functools import cached_property
from typing import TYPE_CHECKING, Any, ClassVar

from django.db.models import QuerySet
from django.http import HttpRequest
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html, format_html_join
from django.utils.translation import gettext as _
from wagtail.admin.ui.tables import Column, DateColumn, UpdatedAtColumn, UserColumn
from wagtail.admin.views.generic import CreateView, EditView, IndexView, InspectView
from wagtail.admin.views.generic.chooser import ChooseView
from wagtail.admin.viewsets.chooser import ChooserViewSet
from wagtail.admin.viewsets.model import ModelViewSet
from wagtail.log_actions import log

from .enums import BundleStatus
from .models import Bundle
from .notifications import notify_slack_of_publication_start, notify_slack_of_publish_end, notify_slack_of_status_change

if TYPE_CHECKING:
    from django.db.models.fields import Field
    from django.http import HttpResponseBase
    from django.utils.safestring import SafeString


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

    actions: ClassVar[list[str]] = ["edit", "save-and-approve", "publish"]
    template_name = "bundles/wagtailadmin/edit.html"
    has_content_changes: bool = False
    start_time: float | None = None

    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> "HttpResponseBase":
        if (instance := self.get_object()) and instance.status == BundleStatus.RELEASED:
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
            elif "action-publish" in self.request.POST:
                data["status"] = BundleStatus.RELEASED.value
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
        elif instance.status == BundleStatus.RELEASED.value:
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
        if self.action == "publish" or (self.action == "edit" and self.object.status == BundleStatus.RELEASED):
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

        context["show_save_and_approve"] = (
            self.object.can_be_approved and self.form.for_user.pk != self.object.created_by_id
        )
        context["show_publish"] = (
            self.object.status == BundleStatus.APPROVED and not self.object.scheduled_publication_date
        )

        return context


class BundleInspectView(InspectView):
    """The Bundle inspect view class."""

    template_name = "bundles/wagtailadmin/inspect.html"

    def get_fields(self) -> list[str]:
        """Returns the list of fields to include in the inspect view."""
        return ["name", "status", "created_at", "created_by", "approved", "scheduled_publication", "pages"]

    def get_field_label(self, field_name: str, field: "Field") -> str:
        match field_name:
            case "approved":
                return _("Approval status")
            case "scheduled_publication":
                return _("Scheduled publication")
            case "pages":
                return _("Pages")
            case _:
                return super().get_field_label(field_name, field)  # type: ignore[no-any-return]

    def get_field_display_value(self, field_name: str, field: "Field") -> Any:
        """Allows customising field display in the inspect class.

        This allows us to use get_FIELDNAME_display_value methods.
        """
        value_func = getattr(self, f"get_{field_name}_display_value", None)
        if value_func is not None:
            return value_func()

        return super().get_field_display_value(field_name, field)

    def get_approved_display_value(self) -> str:
        """Custom approved by formatting. Varies based on status, and approver/time of approval."""
        if self.object.status in [BundleStatus.APPROVED, BundleStatus.RELEASED]:
            if self.object.approved_by_id and self.object.approved_at:
                return f"{self.object.approved_by} on {self.object.approved_at}"
            return _("Unknown approval data")
        return _("Pending approval")

    def get_scheduled_publication_display_value(self) -> str:
        """Displays the scheduled publication date, if set."""
        return self.object.scheduled_publication_date or _("No scheduled publication")

    def get_pages_display_value(self) -> "SafeString":
        """Returns formatted markup for Pages linked to the Bundle."""
        pages = self.object.get_bundled_pages().specific()
        data = (
            (
                reverse("wagtailadmin_pages:edit", args=(page.pk,)),
                page.get_admin_display_title(),
                page.get_verbose_name(),
                (
                    page.current_workflow_state.current_task_state.task.name
                    if page.current_workflow_state
                    else "not in a workflow"
                ),
                reverse("wagtailadmin_pages:view_draft", args=(page.pk,)),
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


class BundleIndexView(IndexView):
    """The Bundle index view class.

    We adjust the queryset and change the edit URL based on the bundle status.
    """

    model = Bundle

    def get_queryset(self) -> QuerySet[Bundle]:
        """Modifies the Bundle queryset with the related created_by ForeignKey selected to avoid N+1 queries."""
        queryset: QuerySet[Bundle] = super().get_queryset()

        return queryset.select_related("created_by")

    def get_edit_url(self, instance: Bundle) -> str | None:
        """Override the default edit url to disable the edit URL for released bundles."""
        if instance.status != BundleStatus.RELEASED:
            edit_url: str | None = super().get_edit_url(instance)
            return edit_url
        return None

    def get_copy_url(self, instance: Bundle) -> str | None:
        """Disables the bundle copy."""
        return None

    @cached_property
    def columns(self) -> list[Column]:
        """Defines the list of desired columns in the listing."""
        return [
            self._get_title_column("__str__"),
            Column("scheduled_publication_date"),
            Column("get_status_display", label=_("Status")),
            UpdatedAtColumn(),
            DateColumn(name="created_at", label=_("Added"), sort_key="created_at"),
            UserColumn("created_by", label=_("Added by")),
            DateColumn(name="approved_at", label=_("Approved at"), sort_key="approved_at"),
            UserColumn("approved_by"),
        ]


class BundleChooseView(ChooseView):
    """The Bundle choose view class. Used in choosers."""

    icon = "boxes-stacked"

    @property
    def columns(self) -> list[Column]:
        """Defines the list of desired columns in the chooser."""
        return [
            *super().columns,
            Column("scheduled_publication_date"),
            UserColumn("created_by"),
        ]

    def get_object_list(self) -> QuerySet[Bundle]:
        """Overrides the default object list to only fetch the fields we're using."""
        queryset: QuerySet[Bundle] = Bundle.objects.select_related("created_by").only("name", "created_by")
        return queryset


class BundleChooserViewSet(ChooserViewSet):
    """Defines the chooser viewset for Bundles."""

    model = Bundle
    icon = "boxes-stacked"
    choose_view_class = BundleChooseView

    def get_object_list(self) -> QuerySet[Bundle]:
        """Only return editable bundles."""
        queryset: QuerySet[Bundle] = self.model.objects.editable()
        return queryset


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
    chooser_viewset_class = BundleChooserViewSet
    list_filter: ClassVar[list[str]] = ["status", "created_by"]
    add_to_admin_menu = True
    inspect_view_enabled = True


bundle_viewset = BundleViewSet("bundle")
bundle_chooser_viewset = BundleChooserViewSet("bundle_chooser")

BundleChooserWidget = bundle_chooser_viewset.widget_class