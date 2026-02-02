"""Tests for core wagtail hooks."""

from http import HTTPStatus

from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse
from wagtail.models import PageLogEntry
from wagtail.test.utils import WagtailTestUtils

from cms.articles.tests.factories import StatisticalArticlePageFactory
from cms.users.tests.factories import UserFactory


class PageEditViewAuditLogTestCase(WagtailTestUtils, TestCase):
    """Tests for the page edit view audit logging via before_edit_page hook."""

    @classmethod
    def setUpTestData(cls):
        cls.superuser = cls.create_superuser(username="admin")
        cls.other_user = UserFactory(is_superuser=True)
        cls.page = StatisticalArticlePageFactory(title="Test Article")

    def setUp(self):
        self.client.force_login(self.superuser)
        self.edit_url = reverse("wagtailadmin_pages:edit", args=[self.page.pk])

    def test_edit_view__creates_audit_log_entry(self):
        """Test that viewing the page edit view creates an audit log entry."""
        PageLogEntry.objects.filter(page_id=self.page.pk, action="pages.edit_view").delete()

        response = self.client.get(self.edit_url)

        self.assertEqual(response.status_code, HTTPStatus.OK)

        log_entry = PageLogEntry.objects.filter(page_id=self.page.pk, action="pages.edit_view").first()
        self.assertIsNotNone(log_entry)
        self.assertEqual(log_entry.user, self.superuser)

    @override_settings(CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}})
    def test_edit_view__audit_log_cooldown_prevents_duplicate_entries(self):
        """Test that viewing the page edit view multiple times within the cooldown period
        only creates one audit log entry.
        """
        PageLogEntry.objects.filter(page_id=self.page.pk, action="pages.edit_view").delete()
        cache.clear()

        # First visit - should create a log entry
        self.client.get(self.edit_url)
        first_count = PageLogEntry.objects.filter(page_id=self.page.pk, action="pages.edit_view").count()
        self.assertEqual(first_count, 1)

        # Second visit within cooldown - should NOT create another log entry
        self.client.get(self.edit_url)
        second_count = PageLogEntry.objects.filter(page_id=self.page.pk, action="pages.edit_view").count()
        self.assertEqual(second_count, 1)

        # Third visit within cooldown - still no new entry
        self.client.get(self.edit_url)
        third_count = PageLogEntry.objects.filter(page_id=self.page.pk, action="pages.edit_view").count()
        self.assertEqual(third_count, 1)

    @override_settings(CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}})
    def test_edit_view__audit_log_cooldown_allows_new_entry_after_expiry(self):
        """Test that a new audit log entry is created after the cooldown expires."""
        PageLogEntry.objects.filter(page_id=self.page.pk, action="pages.edit_view").delete()
        cache.clear()

        # First visit
        self.client.get(self.edit_url)
        first_count = PageLogEntry.objects.filter(page_id=self.page.pk, action="pages.edit_view").count()
        self.assertEqual(first_count, 1)

        # Clear cache to simulate cooldown expiry
        cache.clear()

        # Second visit after cooldown expiry - should create a new log entry
        self.client.get(self.edit_url)
        second_count = PageLogEntry.objects.filter(page_id=self.page.pk, action="pages.edit_view").count()
        self.assertEqual(second_count, 2)

    @override_settings(CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}})
    def test_edit_view__audit_log_different_users_get_separate_cooldowns(self):
        """Test that different users have separate cooldown periods."""
        PageLogEntry.objects.filter(page_id=self.page.pk, action="pages.edit_view").delete()
        cache.clear()

        # First user views the page
        self.client.force_login(self.superuser)
        self.client.get(self.edit_url)

        # Second user views the same page - should also create a log entry
        self.client.force_login(self.other_user)
        self.client.get(self.edit_url)

        log_entries = PageLogEntry.objects.filter(page_id=self.page.pk, action="pages.edit_view")
        self.assertEqual(log_entries.count(), 2)

        users = set(log_entries.values_list("user_id", flat=True))
        self.assertEqual(users, {self.superuser.pk, self.other_user.pk})

    @override_settings(CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}})
    def test_edit_view__audit_log_different_pages_get_separate_cooldowns(self):
        """Test that different pages have separate cooldown periods for the same user."""
        other_page = StatisticalArticlePageFactory(title="Other Article")
        PageLogEntry.objects.filter(action="pages.edit_view").delete()
        cache.clear()

        # View first page
        self.client.get(self.edit_url)

        # View second page - should also create a log entry
        self.client.get(reverse("wagtailadmin_pages:edit", args=[other_page.pk]))

        log_entries = PageLogEntry.objects.filter(action="pages.edit_view")
        self.assertEqual(log_entries.count(), 2)

        page_ids = set(log_entries.values_list("page_id", flat=True))
        self.assertEqual(page_ids, {self.page.pk, other_page.pk})
