from functools import cached_property
from typing import TYPE_CHECKING, Any, Union

from django.db.models import QuerySet
from django.urls import include, path
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _
from wagtail import hooks
from wagtail.admin.ui.components import Component
from wagtail.admin.widgets import PageListingButton
from wagtail.log_actions import LogFormatter
from wagtail.permission_policies import ModelPermissionPolicy

from . import admin_urls
from .models import Bundle, BundledPageMixin
from .viewsets import bundle_chooser_viewset, bundle_viewset

if TYPE_CHECKING:
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
    return [bundle_viewset, bundle_chooser_viewset]


class PageAddToBundleButton(PageListingButton):
    """Defines the 'Add to Bundle' button to use in different contexts in the admin."""

    label = _("Add to Bundle")
    icon_name = "boxes-stacked"
    aria_label_format = _("Add '%(title)s' to a bundle")
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


@hooks.register("before_edit_page")
def preset_golive_date(request: "HttpRequest", page: "Page") -> None:
    """Implements the before_edit_page to preset the golive date on pages in active bundles.

    @see https://docs.wagtail.org/en/stable/reference/hooks.html#before-edit-page.
    """
    if not isinstance(page, BundledPageMixin):
        return

    if not page.in_active_bundle:
        return

    scheduled_date = page.active_bundle.scheduled_publication_date  # type: ignore[union-attr]
    # note: ignoring union-attr because we already check that the page is in an active bundle.
    if not scheduled_date:
        return

    # note: ignoring
    # - attr-defined because mypy thinks page is only a BundledPageMixin class, rather than Page and BundledPageMixin.
    # - union-attr because active_bundle can be none, but we check for that above
    if now() < scheduled_date and scheduled_date != page.go_live_at:  # type: ignore[attr-defined]
        # pre-set the scheduled publishing time
        page.go_live_at = scheduled_date  # type: ignore[attr-defined]


class LatestBundlesPanel(Component):
    """The admin dashboard panel for showing the latest bundles."""

    name = "latest_bundles"
    order = 150
    template_name = "bundles/wagtailadmin/panels/latest_bundles.html"

    def __init__(self, request: "HttpRequest") -> None:
        self.request = request
        self.permission_policy = ModelPermissionPolicy(Bundle)

    @cached_property
    def is_shown(self) -> bool:
        """Determine if the panel is shown based on whether the user can modify it."""
        has_permission: bool = self.permission_policy.user_has_any_permission(
            self.request.user, {"add", "change", "delete", "view"}
        )
        return has_permission

    def get_latest_bundles(self) -> QuerySet[Bundle]:
        """Returns the latest 10 bundles if the panel is shown."""
        queryset: QuerySet[Bundle] = Bundle.objects.none()
        if self.is_shown:
            queryset = Bundle.objects.active().select_related("created_by")[:10]

        return queryset

    def get_context_data(self, parent_context: "RenderContext") -> "RenderContext":
        """Adds the request, the latest bundles and whether the panel is shown to the panel context."""
        context = super().get_context_data(parent_context)
        context["request"] = self.request
        context["bundles"] = self.get_latest_bundles()
        context["is_shown"] = self.is_shown
        return context


@hooks.register("construct_homepage_panels")
def add_latest_bundles_panel(request: "HttpRequest", panels: list[Component]) -> None:
    """Adds the LatestBundlesPanel to the list of Wagtail admin dashboard panels.

    @see https://docs.wagtail.org/en/stable/reference/hooks.html#construct-homepage-panels
    """
    panels.append(LatestBundlesPanel(request))


@hooks.register("register_log_actions")
def register_bundle_log_actions(actions: "LogActionRegistry") -> None:
    """Registers custom logging actions.

    @see https://docs.wagtail.org/en/stable/extending/audit_log.html
    @see https://docs.wagtail.org/en/stable/reference/hooks.html#register-log-actions
    """

    @actions.register_action("bundles.update_status")
    class ChangeBundleStatus(LogFormatter):  # pylint: disable=unused-variable
        """LogFormatter class for the bundle status change actions."""

        label = _("Change bundle status")

        def format_message(self, log_entry: "ModelLogEntry") -> Any:
            """Returns the formatted log message."""
            try:
                return _(f"Changed the bundle status from '{log_entry.data["old"]}' to '{log_entry.data["new"]}'")
            except KeyError:
                return _("Changed the bundle status")

    @actions.register_action("bundles.approve")
    class ApproveBundle(LogFormatter):  # pylint: disable=unused-variable
        """LogFormatter class for the bundle approval actions."""

        label = _("Approve bundle")

        def format_message(self, log_entry: "ModelLogEntry") -> Any:
            """Returns the formatted log message."""
            try:
                return _(f"Approved the bundle. (Old status: '{log_entry.data["old"]}')")
            except KeyError:
                return _("Approved the bundle")
