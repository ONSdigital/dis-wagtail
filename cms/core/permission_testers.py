from django.conf import settings
from wagtail.models import PagePermissionTester

from cms.bundles.utils import in_active_bundle
from cms.workflows.utils import is_page_ready_to_publish


class BasePagePermissionTester(PagePermissionTester):
    """Base class for page permission testers in the CMS."""

    def can_add_subpage(self) -> bool:
        """Determine if a subpage can be added under this page.
        Return False if the page's language doesn't match the default site language (English).
        This enforces that English pages must be created first, then translated, disallowing creation of pages in other
        languages first.
        """
        if self.page.locale.language_code != settings.LANGUAGE_CODE:
            return False
        can_add: bool = super().can_add_subpage()
        return can_add

    def can_copy(self) -> bool:
        """Determine if this can be copied.
        Return False if the page's language doesn't match the default site language (English).
        This enforces that English pages must be created first, then translated, disallowing creation of pages in other
        languages first via copying.
        """
        if self.page.locale.language_code != settings.LANGUAGE_CODE:
            return False
        can_copy_page: bool = super().can_copy()
        return can_copy_page

    def can_lock(self) -> bool:
        """Overrides the core can_lock to prevent superusers from manually locking workflow tasks.

        For all other ones, defer to core, even if there is a tad of repeat logic.
        """
        if current_workflow_task := self.page.current_workflow_task:
            can_lock_via_task: bool = current_workflow_task.user_can_lock(self.page, self.user)
            return can_lock_via_task

        can_lock: bool = super().can_lock()
        return can_lock

    def can_publish(self) -> bool:
        """Overrides the core can_publish to extend with ONS publishing logic.

        To manually or schedule publish:
        - the page must not be in an active bundle
        - the page must be in the approved (i.e. in the "Ready to publish" workflow step)
        """
        if in_active_bundle(self.page):
            return False

        if not is_page_ready_to_publish(self.page):
            return False

        can_publish: bool = super().can_publish()
        return can_publish

    def can_publish_subpage(self) -> bool:
        """Overrides the core can_publish_subpage to extend with ONS publishing logic.

        Core description:
        Niggly special case for creating and publishing a page in one go.
        Differs from can_publish in that we want to be able to publish subpages of root, but not
        to be able to publish root itself. (Also, can_publish_subpage returns false if the page
        does not allow subpages at all.)
        """
        if in_active_bundle(self.page):
            return False

        if not is_page_ready_to_publish(self.page):
            return False

        can_publish_subpage: bool = super().can_publish_subpage()
        return can_publish_subpage
