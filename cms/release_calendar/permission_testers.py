from cms.core.permission_testers import BasePagePermissionTester


class ReleaseCalendarPagePermissionTester(BasePagePermissionTester):
    """Permission tester for Release Calendar pages.

    Release Calendar pages are never unpublished; the `status` field is set to `CANCELLED`
    instead.

    Note: The "never-published only" delete rule is enforced at the `before_delete_page`
    hook layer and is not part of this permission tester.
    """

    def can_unpublish(self) -> bool:
        return False
