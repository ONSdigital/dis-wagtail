from typing import TYPE_CHECKING

from django.urls import reverse
from django.utils.html import format_html
from wagtail.locks import WorkflowLock

from cms.bundles.permissions import user_can_manage_bundles

if TYPE_CHECKING:
    from django.utils.safestring import SafeString

    from cms.users.models import User


class PageReadyToBePublishedLock(WorkflowLock):
    """A lock that is enabled when the page is in a bundle that is ready to be published."""

    def for_user(self, user: User) -> bool:
        return (
            getattr(self.object, "active_bundle", None) is not None
            and self.object.active_bundle.is_ready_to_be_published
        )

    def get_message(self, user: User) -> str | SafeString:
        if user_can_manage_bundles(user):
            return format_html(
                "This page is included in a bundle that is ready to be published. You must revert the bundle "
                "to <strong>Draft</strong> or <strong>In preview</strong> in order to make further changes. "
                '<span class="buttons">'
                '<a type="button" class="button button-small button-secondary" href="{url}">Manage bundle</a></span>',
                url=reverse("bundle:edit", args=(self.object.active_bundle.pk,)),
            )
        return format_html(
            'This page cannot be changed as it included in the "{bundle_title}" bundle which is ready to be published.',
            bundle_title=self.object.active_bundle.name,
        )

    def get_description(self, user: User, can_lock: bool = False) -> SafeString:
        """Displayed in the sidebar info panel."""
        if user_can_manage_bundles(user):
            message = (
                'You must revert the bundle "<a href="{url}">{bundle_title}</a>" to <strong>Draft</strong> or '
                '<strong>In preview</strong> in order to make further changes. <a href="{url}">Manage bundle</a>.'
            )
            return format_html(
                message,
                url=reverse("bundle:edit", args=(self.object.active_bundle.pk,)),
                bundle_title=self.object.active_bundle.name,
            )
        return format_html(
            'This page cannot be changed as it included in the "{bundle_title}" bundle which is ready to be published.',
            bundle_title=self.object.active_bundle.name,
        )
