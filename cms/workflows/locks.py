from typing import TYPE_CHECKING

from django.urls import reverse
from django.utils.html import format_html
from wagtail.locks import WorkflowLock

from cms.bundles.permissions import user_can_manage_bundles
from cms.bundles.utils import in_bundle_ready_to_be_published

if TYPE_CHECKING:
    from django.utils.safestring import SafeString

    from cms.users.models import User


class PageReadyToBePublishedLock(WorkflowLock):
    """A page workflow lock.

    It comes in effect when the page enters the "Ready to be published" workflow step.
    The page can be "unlocked" by moving back to the previous workflow step.
    If the page is in a bundle that is ready to be published, then the bundle must be taken out of
    "Ready to be published" first.
    """

    def get_message(self, user: User) -> str | SafeString:
        """The lock message displayed at the top of the page."""
        if in_bundle_ready_to_be_published(self.object):
            return self.get_in_bundle_message(user)

        return self.get_generic_message(user)

    def get_description(self, user: User, _can_lock: bool = False) -> str | SafeString:
        """Displayed in the sidebar info panel."""
        if in_bundle_ready_to_be_published(self.object):
            return self.get_in_bundle_description(user)

        return self.get_generic_message(user)

    def get_generic_message(self, user: User) -> str | SafeString:
        if self.for_user(user):
            return format_html(
                "This page cannot be edited as it is <strong>{status}</strong>.", status="Ready to be published"
            )

        return ""

    def get_in_bundle_message(self, user: User) -> str | SafeString:
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

    def get_in_bundle_description(self, user: User) -> SafeString:
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
