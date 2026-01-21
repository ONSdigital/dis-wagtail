from django.conf import settings
from wagtail.models import PagePermissionTester


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
