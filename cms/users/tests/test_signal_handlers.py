from django.test import TestCase
from django.urls import reverse
from wagtail.test.utils import WagtailTestUtils
from wagtail.users.models import UserProfile


class AuditLogTestCase(WagtailTestUtils, TestCase):
    login_url = reverse("wagtailadmin_login")
    logout_url = reverse("wagtailadmin_logout")

    @classmethod
    def setUpTestData(cls) -> None:
        cls.user = cls.create_superuser(username="admin", password="password")

    def test_login(self):
        with self.assertLogs("cms.users") as logs:
            self.client.force_login(self.user)

        self.assertEqual(len(logs.records), 1)

        record = logs.records[0]

        self.assertEqual(record.msg, "User logged in")
        self.assertEqual(record.user_id, self.user.id)
        self.assertEqual(record.event, "user_logged_in")
        self.assertIsNone(record.ip_address)
        self.assertIsNone(record.user_agent)

    def test_logout(self):
        with self.assertLogs("cms.users"):
            self.client.force_login(self.user)

        with self.assertLogs("cms.users") as logs:
            self.client.logout()

        self.assertEqual(len(logs.records), 1)

        record = logs.records[0]

        self.assertEqual(record.msg, "User logged out")
        self.assertEqual(record.user_id, self.user.id)
        self.assertEqual(record.event, "user_logged_out")
        self.assertIsNone(record.ip_address)
        self.assertIsNone(record.user_agent)

    def test_logout_without_login(self):
        with self.assertNoLogs("cms.users"):
            self.client.logout()

    def test_login_failed(self):
        with self.assertLogs("cms.users") as logs:
            self.client.login(username="username", password="password")

        self.assertEqual(len(logs.records), 1)

        record = logs.records[0]

        self.assertEqual(record.msg, "Login failed")
        self.assertEqual(record.username, "username")
        self.assertEqual(record.event, "user_login_failed")
        self.assertIsNone(record.ip_address)
        self.assertIsNone(record.user_agent)

    def test_wagtail_login(self):
        with self.assertLogs("cms.users") as logs:
            response = self.client.post(
                self.login_url,
                data={"username": self.user.username, "password": "password"},
                headers={"User-Agent": "my browser"},
            )

        self.assertEqual(response.status_code, 302)

        self.assertEqual(len(logs.records), 1)

        record = logs.records[0]

        self.assertEqual(record.msg, "User logged in")
        self.assertEqual(record.user_id, self.user.id)
        self.assertEqual(record.event, "user_logged_in")
        self.assertEqual(record.ip_address, "127.0.0.1")
        self.assertEqual(record.user_agent, "my browser")

    def test_wagtail_logout(self):
        with self.assertLogs("cms.users"):
            self.client.force_login(self.user)

        with self.assertLogs("cms.users") as logs:
            response = self.client.post(
                self.logout_url,
                headers={"User-Agent": "my browser"},
            )

        self.assertEqual(response.status_code, 302)

        self.assertEqual(len(logs.records), 1)

        record = logs.records[0]

        self.assertEqual(record.msg, "User logged out")
        self.assertEqual(record.user_id, self.user.id)
        self.assertEqual(record.event, "user_logged_out")
        self.assertEqual(record.ip_address, "127.0.0.1")
        self.assertEqual(record.user_agent, "my browser")

    def test_wagtail_login_failed(self):
        with self.assertLogs("cms.users") as logs:
            response = self.client.post(
                self.login_url,
                data={"username": self.user.username, "password": "wrong_password"},
                headers={"User-Agent": "my browser"},
            )

        self.assertEqual(response.status_code, 200)

        self.assertEqual(len(logs.records), 1)

        record = logs.records[0]

        self.assertEqual(record.msg, "Login failed")
        self.assertEqual(record.username, self.user.username)
        self.assertEqual(record.event, "user_login_failed")
        self.assertEqual(record.ip_address, "127.0.0.1")
        self.assertEqual(record.user_agent, "my browser")


class UserProfileSignalTestCase(WagtailTestUtils, TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.user = cls.create_superuser(username="admin", password="password")
        cls.profile = UserProfile.get_for_user(cls.user)

    def test_user_profile_submitted_notifications_disabled_on_creation(self):
        # only "submitted notifications" are disabled as they are global
        # the rest are left as they are as they require interaction with the page/workflow-enabled snippet
        self.assertFalse(self.profile.submitted_notifications)
        self.assertTrue(self.profile.approved_notifications)
        self.assertTrue(self.profile.rejected_notifications)
        self.assertTrue(self.profile.updated_comments_notifications)

    def test_user_profile_notifications_not_changed_on_update(self):
        self.profile.submitted_notifications = True
        self.profile.save()

        self.profile.refresh_from_db()

        self.assertTrue(self.profile.submitted_notifications)
