from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import Group
from django.test import TestCase
from django.utils import timezone
from wagtail.test.utils import WagtailTestUtils

from cms.release_calendar.permission_testers import ReleaseCalendarPagePermissionTester
from cms.release_calendar.tests.factories import ReleaseCalendarPageFactory
from cms.users.tests.factories import UserFactory


class ReleaseCalendarPagePermissionTesterTests(WagtailTestUtils, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.publishing_admin = UserFactory(username="release_admin")
        cls.publishing_admin.groups.add(Group.objects.get(name=settings.PUBLISHING_ADMINS_GROUP_NAME))
        cls.publishing_officer = UserFactory(username="release_officer")
        cls.publishing_officer.groups.add(Group.objects.get(name=settings.PUBLISHING_OFFICERS_GROUP_NAME))
        cls.superuser = cls.create_superuser(username="release_superuser")
        cls.user = UserFactory(access_admin=True, username="release_non_editor")

    def _users(self):
        return [self.superuser, self.publishing_admin, self.publishing_officer, self.user]

    def test_can_unpublish_always_false(self):
        page = ReleaseCalendarPageFactory(
            first_published_at=timezone.now() - timedelta(days=5),
            last_published_at=timezone.now() - timedelta(days=1),
            live=True,
        )
        for user in self._users():
            with self.subTest(f"{user=} cannot unpublish a release calendar page"):
                tester = ReleaseCalendarPagePermissionTester(user=user, page=page)
                self.assertFalse(tester.can_unpublish())

    def test_can_delete_defers_to_base(self):
        # The release calendar tester delegates `can_delete` to the base behaviour.
        # The "never-published only" rule for release calendar pages is enforced at
        # the `before_delete_page` hook layer instead.
        page = ReleaseCalendarPageFactory(live=False, first_published_at=None, last_published_at=None)
        for user in [self.superuser, self.publishing_admin, self.publishing_officer]:
            with self.subTest(f"{user=} can delete a release calendar page (hook-enforced rule)"):
                tester = ReleaseCalendarPagePermissionTester(user=user, page=page)
                self.assertTrue(tester.can_delete())

    def test_regular_user_cannot_delete(self):
        page = ReleaseCalendarPageFactory(live=False, first_published_at=None, last_published_at=None)
        tester = ReleaseCalendarPagePermissionTester(user=self.user, page=page)
        self.assertFalse(tester.can_delete())
