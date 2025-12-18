from typing import TYPE_CHECKING, Any, Union, cast

from django.db.models import QuerySet
from django.urls import include, path
from django.utils.functional import cached_property
from wagtail import hooks
from wagtail.admin.ui.components import Component
from wagtail.admin.widgets import PageListingButton
from wagtail.log_actions import LogFormatter
from wagtail.permission_policies import ModelPermissionPolicy

from . import admin_urls
from .mixins import BundledPageMixin
from .models import Bundle
from .viewsets.bundle import bundle_viewset
from .viewsets.bundle_chooser import bundle_chooser_viewset
from .viewsets.bundle_page_chooser import bundle_page_chooser_viewset

if TYPE_CHECKING:
    from typing import Optional

    from django.http import HttpRequest
    from django.urls import URLPattern
    from django.urls.resolvers import URLResolver
    from laces.typing import RenderContext
    from wagtail.log_actions import LogActionRegistry
    from wagtail.models import ModelLogEntry, Page

    from cms.users.models import User


@hooks.register("register_admin_viewset")
def register_viewset() -> list:
    """Registers the bundle viewsets.

    @see https://docs.wagtail.org/en/stable/reference/hooks.html#register-admin-viewset
    """
    return [bundle_viewset, bundle_chooser_viewset, bundle_page_chooser_viewset]


class PageAddToBundleButton(PageListingButton):
    """Defines the 'Add to Bundle' button to use in different contexts in the admin."""

    label = "Add to Bundle"
    icon_name = "boxes-stacked"
    aria_label_format = "Add '%(title)s' to a bundle"
    url_name = "bundles:add_to_bundle"

    @property
    def permission_policy(self) -> ModelPermissionPolicy:
        """Informs the permission policy to use Bundle-derived model permissions."""
        return ModelPermissionPolicy(Bundle)

    @property
    def show(self) -> bool:
        """Determines whether the button should be shown.

        We only want it for pages inheriting from BundledPageMixin that are not in an active bundle.
        """
        if not isinstance(self.page, BundledPageMixin):
            return False

        if self.page.in_active_bundle:
            return False

        # Note: limit to pages that are not in an active bundle
        can_show: bool = (
            self.page_perms.can_edit() or self.page_perms.can_publish()
        ) and self.permission_policy.user_has_any_permission(self.user, ["add", "change", "delete"])
        return can_show


@hooks.register("register_page_header_buttons")
def page_header_buttons(page: "Page", user: "User", view_name: str, next_url: str | None = None) -> PageListingButton:  # pylint: disable=unused-argument
    """Registers the add to bundle button in the buttons shown in the page add/edit header.

    @see https://docs.wagtail.org/en/stable/reference/hooks.html#register-page-header-buttons.
    """
    yield PageAddToBundleButton(page=page, user=user, priority=10, next_url=next_url)


@hooks.register("register_page_listing_buttons")
def page_listing_buttons(page: "Page", user: "User", next_url: str | None = None) -> PageListingButton:
    """Registers the add to bundle button in the buttons shown in the page listing.

    @see https://docs.wagtail.org/en/stable/reference/hooks.html#register_page_listing_buttons.
    """
    yield PageAddToBundleButton(page=page, user=user, priority=10, next_url=next_url)


@hooks.register("register_admin_urls")
def register_admin_urls() -> list[Union["URLPattern", "URLResolver"]]:
    """Registers the admin urls for Bundles.

    @see https://docs.wagtail.org/en/stable/reference/hooks.html#register-admin-urls.
    """
    return [path("bundles/", include(admin_urls))]


class LatestBundlesPanel(Component):
    """The admin dashboard panel for showing the latest bundles."""

    name = "latest_bundles"
    order = 150
    template_name = "bundles/wagtailadmin/panels/latest_bundles.html"
    num_bundles = 10

    def __init__(self, request: "HttpRequest") -> None:
        self.request = request
        self.permission_policy = ModelPermissionPolicy(Bundle)

    @cached_property
    def is_shown(self) -> bool:
        """Determine if the panel is shown based on whether the user can modify it."""
        has_permission: bool = self.permission_policy.user_has_any_permission(
            self.request.user, {"add", "change", "delete"}
        )
        return has_permission

    def get_latest_bundles(self) -> QuerySet[Bundle]:
        """Returns the latest 10 bundles if the panel is shown."""
        queryset: QuerySet[Bundle] = Bundle.objects.none()
        if self.is_shown:
            queryset = Bundle.objects.active()[: self.num_bundles]

        return queryset

    def get_context_data(self, parent_context: "Optional[RenderContext]" = None) -> "Optional[RenderContext]":
        """Adds the request, the latest bundles and whether the panel is shown to the panel context."""
        context = super().get_context_data(parent_context)
        context["request"] = self.request
        context["bundles"] = sorted(self.get_latest_bundles(), key=lambda b: b.name)
        context["is_shown"] = self.is_shown
        context["num_bundles"] = self.num_bundles
        return context


class BundlesInReviewPanel(Component):
    name = "bundles_in_review"
    order = 150
    template_name = "bundles/wagtailadmin/panels/bundles_in_review.html"
    num_bundles = 10

    def __init__(self, request: "HttpRequest") -> None:
        self.request = request
        self.permission_policy = ModelPermissionPolicy(Bundle)

    @cached_property
    def _can_manage(self) -> bool:
        return bool(self.permission_policy.user_has_any_permission(self.request.user, {"add", "change", "delete"}))

    @cached_property
    def is_shown(self) -> bool:
        """Only show to users that can view, but not manage bundles."""
        if self.request.user.is_superuser:
            return True

        has_view_permission = self.permission_policy.user_has_permission(self.request.user, "view")
        return has_view_permission or self._can_manage

    @cached_property
    def bundles(self) -> QuerySet[Bundle]:
        """Returns the latest 10 bundles if the panel is shown."""
        if not self.is_shown:
            return cast(QuerySet[Bundle], Bundle.objects.none())

        queryset: QuerySet[Bundle] = Bundle.objects.previewable().order_by("approved_at")
        if self._can_manage:
            # show all "in preview" for users that can manage.
            return queryset

        # for everyone else, only bundles in the same preview team they are in
        return queryset.filter(teams__team__in=self.request.user.active_team_ids).distinct()  # type: ignore[union-attr]

    def get_context_data(self, parent_context: "Optional[RenderContext]" = None) -> "Optional[RenderContext]":
        """Adds the request, the latest bundles and whether the panel is shown to the panel context."""
        context = super().get_context_data(parent_context)
        context["request"] = self.request
        context["bundles"] = sorted(self.bundles[: self.num_bundles], key=lambda b: b.name)
        context["is_shown"] = self.is_shown
        context["more_link"] = len(self.bundles) > self.num_bundles
        return context


@hooks.register("construct_homepage_panels")
def add_latest_bundles_panel(request: "HttpRequest", panels: list[Component]) -> None:
    """Adds the LatestBundlesPanel to the list of Wagtail admin dashboard panels.

    @see https://docs.wagtail.org/en/stable/reference/hooks.html#construct-homepage-panels
    """
    panels.append(LatestBundlesPanel(request))
    panels.append(BundlesInReviewPanel(request))


@hooks.register("register_log_actions")
def register_bundle_log_actions(actions: "LogActionRegistry") -> None:
    """Registers custom logging actions.

    @see https://docs.wagtail.org/en/stable/extending/audit_log.html
    @see https://docs.wagtail.org/en/stable/reference/hooks.html#register-log-actions
    """

    @actions.register_action("bundles.update_status")
    class ChangeBundleStatus(LogFormatter):  # pylint: disable=unused-variable
        """LogFormatter class for the bundle status change actions."""

        label = "Change bundle status"

        def format_message(self, log_entry: "ModelLogEntry") -> Any:
            """Returns the formatted log message."""
            try:
                return f"Changed the bundle status from '{log_entry.data['old']}' to '{log_entry.data['new']}'"
            except KeyError:
                return "Changed the bundle status"

    @actions.register_action("bundles.approve")
    class ApproveBundle(LogFormatter):  # pylint: disable=unused-variable
        """LogFormatter class for the bundle approval actions."""

        label = "Approve bundle"

        def format_message(self, log_entry: "ModelLogEntry") -> Any:
            """Returns the formatted log message."""
            try:
                return f"Approved the bundle. (Old status: '{log_entry.data['old']}')"
            except KeyError:
                return "Approved the bundle"

    @actions.register_action("bundles.preview")
    class PreviewBundle(LogFormatter):  # pylint: disable=unused-variable
        """LogFormatter class for the bundle item preview actions."""

        label = "Preview bundle item"

        def format_message(self, log_entry: "ModelLogEntry") -> Any:
            """Returns the formatted log message."""
            try:
                return f"Previewed {log_entry.data['type']} '{log_entry.data['title']}'."
            except KeyError:
                return "Previewed an item."

    @actions.register_action("bundles.preview.attempt")
    class PreviewBundleAttempt(LogFormatter):  # pylint: disable=unused-variable
        """LogFormatter class for the bundle item preview attempt actions."""

        label = "Attempt bundle item preview"

        def format_message(self, log_entry: "ModelLogEntry") -> Any:
            """Returns the formatted log message."""
            try:
                return f"Attempted preview of {log_entry.data['type']} '{log_entry.data['title']}'."
            except KeyError:
                return "Attempted to preview an item."

    @actions.register_action("bundles.create")
    class CreateBundle(LogFormatter):  # pylint: disable=unused-variable
        """LogFormatter class for bundle creation actions."""

        label = "Create bundle"

        def format_message(self, log_entry: "ModelLogEntry") -> Any:
            """Returns the formatted log message."""
            return "Created bundle"

    @actions.register_action("bundles.team_added")
    class AddBundleTeam(LogFormatter):  # pylint: disable=unused-variable
        """LogFormatter class for adding preview teams to bundles."""

        label = "Add preview team to bundle"

        def format_message(self, log_entry: "ModelLogEntry") -> Any:
            """Returns the formatted log message."""
            try:
                return f"Added preview team '{log_entry.data['team_name']}'"
            except KeyError:
                return "Added preview team"

    @actions.register_action("bundles.team_removed")
    class RemoveBundleTeam(LogFormatter):  # pylint: disable=unused-variable
        """LogFormatter class for removing preview teams from bundles."""

        label = "Remove preview team from bundle"

        def format_message(self, log_entry: "ModelLogEntry") -> Any:
            """Returns the formatted log message."""
            try:
                return f"Removed preview team '{log_entry.data['team_name']}'"
            except KeyError:
                return "Removed preview team"

    @actions.register_action("bundles.page_added")
    class AddBundlePage(LogFormatter):  # pylint: disable=unused-variable
        """LogFormatter class for adding pages to bundles."""

        label = "Add page to bundle"

        def format_message(self, log_entry: "ModelLogEntry") -> Any:
            """Returns the formatted log message."""
            try:
                return f"Added page '{log_entry.data['page_title']}'"
            except KeyError:
                return "Added page"

    @actions.register_action("bundles.page_removed")
    class RemoveBundlePage(LogFormatter):  # pylint: disable=unused-variable
        """LogFormatter class for removing pages from bundles."""

        label = "Remove page from bundle"

        def format_message(self, log_entry: "ModelLogEntry") -> Any:
            """Returns the formatted log message."""
            try:
                return f"Removed page '{log_entry.data['page_title']}'"
            except KeyError:
                return "Removed page"

    @actions.register_action("bundles.dataset_added")
    class AddBundleDataset(LogFormatter):  # pylint: disable=unused-variable
        """LogFormatter class for adding datasets to bundles."""

        label = "Add dataset to bundle"

        def format_message(self, log_entry: "ModelLogEntry") -> Any:
            """Returns the formatted log message."""
            try:
                return f"Added dataset '{log_entry.data['dataset_title']}'"
            except KeyError:
                return "Added dataset"

    @actions.register_action("bundles.dataset_removed")
    class RemoveBundleDataset(LogFormatter):  # pylint: disable=unused-variable
        """LogFormatter class for removing datasets from bundles."""

        label = "Remove dataset from bundle"

        def format_message(self, log_entry: "ModelLogEntry") -> Any:
            """Returns the formatted log message."""
            try:
                return f"Removed dataset '{log_entry.data['dataset_title']}'"
            except KeyError:
                return "Removed dataset"

    @actions.register_action("bundles.schedule_changed")
    class ChangeBundleSchedule(LogFormatter):  # pylint: disable=unused-variable
        """LogFormatter class for bundle publication date changes."""

        label = "Change bundle schedule"

        def format_message(self, log_entry: "ModelLogEntry") -> Any:
            """Returns the formatted log message."""
            try:
                old = log_entry.data.get("old", "Not set")
                new = log_entry.data.get("new", "Not set")
                return f"Changed publication date from '{old}' to '{new}'"
            except KeyError:
                return "Changed publication date"
