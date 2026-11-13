from django.contrib.auth.models import Permission
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse
from wagtail.log_actions import log
from wagtail.models import ModelLogEntry
from wagtail.test.utils import WagtailTestUtils

from cms.core.middleware import SITE_HISTORY_VIEW_ACTION
from cms.users.tests.factories import UserFactory


class SiteHistoryReadAuditTestCase(WagtailTestUtils, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = cls.create_superuser(username="admin")
        cls.url = reverse("wagtailadmin_reports:site_history")
        cls.results_url = reverse("wagtailadmin_reports:site_history_results")

    def setUp(self):
        self.client.force_login(self.superuser)

    def get_read_entries(self):
        return ModelLogEntry.objects.filter(action=SITE_HISTORY_VIEW_ACTION)

    def test_viewing_site_history_is_logged(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        entry = self.get_read_entries().get()
        self.assertEqual(entry.user, self.superuser)
        self.assertEqual(entry.object_id, str(self.superuser.pk))
        self.assertEqual(entry.data, {"export": None, "results_only": False, "query": ""})

    def test_viewing_site_history_results_is_logged_with_filters(self):
        response = self.client.get(self.results_url, {"action": "wagtail.edit"})

        self.assertEqual(response.status_code, 200)
        entry = self.get_read_entries().get()
        self.assertEqual(entry.data, {"export": None, "results_only": True, "query": "action=wagtail.edit"})

    def test_export_is_identified(self):
        for export_format in ("csv", "xlsx"):
            with self.subTest(export_format=export_format):
                response = self.client.get(self.url, {"export": export_format, "action": "wagtail.edit"})

                self.assertEqual(response.status_code, 200)
                entry = self.get_read_entries().latest("timestamp")
                self.assertEqual(entry.data["export"], export_format)
                self.assertEqual(entry.data["query"], f"export={export_format}&action=wagtail.edit")
                self.assertEqual(entry.message, f"Exported site history ({export_format.upper()})")

    def test_unknown_export_format_is_logged_as_view(self):
        self.client.get(self.url, {"export": "pdf"})

        entry = self.get_read_entries().get()
        self.assertIsNone(entry.data["export"])
        self.assertEqual(entry.message, "Viewed site history")

    @override_settings(CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}})
    def test_cooldown_prevents_duplicate_view_entries(self):
        cache.clear()

        self.client.get(self.url)
        self.client.get(self.results_url, {"action": "wagtail.edit"})
        self.client.get(self.url)

        self.assertEqual(self.get_read_entries().count(), 1)

    @override_settings(CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}})
    def test_cooldown_allows_new_entry_after_expiry(self):
        cache.clear()

        self.client.get(self.url)
        # Simulate cooldown expiry
        cache.clear()
        self.client.get(self.url)

        self.assertEqual(self.get_read_entries().count(), 2)

    @override_settings(CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}})
    def test_different_users_get_separate_cooldowns(self):
        cache.clear()
        other_user = self.create_superuser(username="other_admin")

        self.client.get(self.url)
        self.client.force_login(other_user)
        self.client.get(self.url)

        users = set(self.get_read_entries().values_list("user_id", flat=True))
        self.assertEqual(users, {self.superuser.pk, other_user.pk})

    @override_settings(CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}})
    def test_exports_bypass_cooldown(self):
        cache.clear()

        self.client.get(self.url)
        self.client.get(self.url, {"export": "csv"})
        self.client.get(self.url, {"export": "csv"})

        self.assertEqual(self.get_read_entries().count(), 3)
        self.assertEqual(self.get_read_entries().filter(data__export="csv").count(), 2)

    def test_read_event_is_shown_in_site_history(self):
        self.client.get(self.url)
        response = self.client.get(self.url)

        self.assertContains(response, "Viewed site history")

    def test_read_event_is_emitted_for_protective_monitoring(self):
        with self.assertLogs("cms.audit", level="INFO") as logs:
            self.client.get(self.url)

        record = next(r for r in logs.records if r.event == SITE_HISTORY_VIEW_ACTION)
        self.assertEqual(record.classification, "PROTECTIVE_MONITORING")
        self.assertEqual(record.user_id, self.superuser.pk)
        self.assertEqual(record.email, self.superuser.email)
        self.assertIsNone(record.data["export"])

    def test_export_is_emitted_for_protective_monitoring(self):
        with self.assertLogs("cms.audit", level="INFO") as logs:
            self.client.get(self.url, {"export": "csv"})

        record = next(r for r in logs.records if r.event == SITE_HISTORY_VIEW_ACTION)
        self.assertEqual(record.classification, "PROTECTIVE_MONITORING")
        self.assertEqual(record.data["export"], "csv")

    def test_other_audit_events_are_not_classified(self):
        with self.assertLogs("cms.audit", level="INFO") as logs:
            log(instance=self.superuser, action="wagtail.edit", user=self.superuser)

        self.assertFalse(hasattr(logs.records[0], "classification"))

    def test_non_superuser_admin_read_is_logged(self):
        user = UserFactory()
        user.user_permissions.add(Permission.objects.get(codename="access_admin"))
        self.client.force_login(user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.get_read_entries().get().user, user)

    def test_denied_access_is_not_logged_as_read(self):
        self.client.force_login(UserFactory())

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 302)
        self.assertFalse(self.get_read_entries().exists())

    def test_anonymous_access_is_not_logged_as_read(self):
        self.client.logout()

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 302)
        self.assertFalse(self.get_read_entries().exists())

    def test_other_admin_views_are_not_logged(self):
        self.client.get(reverse("wagtailadmin_home"))

        self.assertFalse(self.get_read_entries().exists())
