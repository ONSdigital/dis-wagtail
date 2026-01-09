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

    def can_publish(self) -> bool:
        """Determine if the page can be published directly.

        Returns False when WAGTAIL_WORKFLOW_REQUIRE_APPROVAL_TO_PUBLISH is True (the default),
        enforcing the approval workflow for all pages. This prevents accidental or unauthorized
        publication of potentially sensitive content.

        For local development, this can be disabled in settings to allow direct publishing.
        """
        if getattr(settings, "WAGTAIL_WORKFLOW_REQUIRE_APPROVAL_TO_PUBLISH", True):
            return False
        can_publish: bool = super().can_publish()
        return can_publish
