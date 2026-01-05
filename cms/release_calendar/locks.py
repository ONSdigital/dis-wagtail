from typing import TYPE_CHECKING, Union

from django.urls import reverse
from django.utils.html import format_html
from wagtail.locks import BaseLock

from cms.bundles.permissions import user_can_manage_bundles

if TYPE_CHECKING:
    from django.utils.safestring import SafeString

    from cms.users.models import User


class ReleasePageInBundleReadyToBePublishedLock(BaseLock):
    """A lock that is enabled when the release calendar page is in a bundle that is ready to be published."""

    def for_user(self, user: User) -> bool:
        return self.object.active_bundle is not None and self.object.active_bundle.is_ready_to_be_published

    def get_message(self, user: User) -> Union[str, SafeString]:
        lock_message = (
            "This release calendar page is linked to a bundle that is ready to be published. "
            "You must unlink them in order to make changes."
        )
        if user_can_manage_bundles(user):
            lock_message = format_html(
                '{} <span class="buttons">'
                '<a type="button" class="button button-small button-secondary" href="{}">{}</a></span>',
                lock_message,
                reverse("bundle:edit", args=(self.object.active_bundle.pk,)),
                "Manage bundle",
            )
        return lock_message

    def get_description(self, user: User) -> SafeString:
        if user_can_manage_bundles(user):
            return format_html(
                'You must unlink the release calendar page from the following bundle: <a href="{url}">{title}</a>.',
                url=reverse("bundle:edit", args=(self.object.active_bundle.pk,)),
                title=self.object.active_bundle.name,
            )
        return format_html(
            "The release calendar page is linked to the '{bundle_title}' bundle which is ready to be published.",
            bundle_title=self.object.active_bundle.name,
        )
