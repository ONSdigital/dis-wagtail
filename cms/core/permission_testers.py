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
        return super().can_add_subpage()
