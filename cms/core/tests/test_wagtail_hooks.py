"""Tests for core wagtail hooks."""

from datetime import timedelta
from http import HTTPStatus

from django.conf import settings
from django.contrib.auth.models import Group
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from wagtail.models import Locale, PageLogEntry
from wagtail.test.utils import WagtailTestUtils

from cms.articles.tests.factories import StatisticalArticlePageFactory
from cms.standard_pages.models import InformationPage
from cms.standard_pages.tests.factories import IndexPageFactory, InformationPageFactory
from cms.users.tests.factories import UserFactory


class PageEditViewAuditLogTestCase(WagtailTestUtils, TestCase):
    """Tests for the page edit view audit logging via before_edit_page hook."""

    @classmethod
    def setUpTestData(cls):
        cls.superuser = cls.create_superuser(username="admin")
        cls.other_user = cls.create_superuser(username="other_admin")
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


class PreventDeleteOfPreviouslyPublishedPageHookTests(WagtailTestUtils, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = cls.create_superuser("admin")
        cls.index_page = IndexPageFactory()

    def setUp(self):
        self.client.force_login(self.superuser)

    def _assert_hook_blocked(self, response, redirect_url):
        self.assertRedirects(response, redirect_url)
        messages = [msg.message.strip() for msg in response.context["messages"]]
        self.assertTrue(
            any("published previously" in msg for msg in messages),
            f"Expected 'published previously' in one of: {messages}",
        )

    def test_delete_blocked_for_previously_published_page(self):
        page = InformationPageFactory(
            parent=self.index_page,
            first_published_at=timezone.now() - timedelta(days=1),
            last_published_at=timezone.now(),
        )
        response = self.client.post(reverse("wagtailadmin_pages:delete", args=[page.pk]), follow=True)
        self._assert_hook_blocked(response, reverse("wagtailadmin_pages:edit", args=[page.pk]))

    def test_delete_blocked_for_previously_published_page_and_redirected_to_next_url(self):
        page = InformationPageFactory(
            parent=self.index_page,
            first_published_at=timezone.now() - timedelta(days=1),
            last_published_at=timezone.now(),
        )
        response = self.client.post(
            reverse("wagtailadmin_pages:delete", args=[page.pk]),
            follow=True,
            query_params={"next": reverse("wagtailadmin_home")},
        )
        # The hook should block the deletion and redirect to the provided next URL, not the edit page
        self._assert_hook_blocked(response, reverse("wagtailadmin_home"))

    def test_delete_allowed_for_never_published_page(self):
        page = InformationPageFactory(parent=self.index_page, live=False)
        page.first_published_at = None
        page.last_published_at = None
        page.save(update_fields=["first_published_at", "last_published_at"])

        response = self.client.get(reverse("wagtailadmin_pages:delete", args=[page.pk]))

        self.assertEqual(response.status_code, 200)

    def test_delete_blocked_when_translation_was_previously_published(self):
        page = InformationPageFactory(parent=self.index_page, live=False)
        page.first_published_at = None
        page.last_published_at = None
        page.save(update_fields=["first_published_at", "last_published_at"])

        welsh_locale = Locale.objects.get(language_code="cy")
        self.index_page.copy_for_translation(welsh_locale, alias=True)
        translation = page.copy_for_translation(welsh_locale)
        translation.first_published_at = timezone.now() - timedelta(days=1)
        translation.last_published_at = timezone.now()
        translation.save(update_fields=["first_published_at", "last_published_at"])

        response = self.client.post(reverse("wagtailadmin_pages:delete", args=[page.pk]), follow=True)
        self._assert_hook_blocked(response, reverse("wagtailadmin_pages:edit", args=[page.pk]))

    def test_delete_blocked_when_original_was_previously_published(self):
        page = InformationPageFactory(
            parent=self.index_page,
            first_published_at=timezone.now() - timedelta(days=1),
            last_published_at=timezone.now(),
        )

        welsh_locale = Locale.objects.get(language_code="cy")
        self.index_page.copy_for_translation(welsh_locale, alias=True)
        translation = page.copy_for_translation(welsh_locale)
        translation.first_published_at = None
        translation.last_published_at = None
        translation.save(update_fields=["first_published_at", "last_published_at"])

        response = self.client.post(reverse("wagtailadmin_pages:delete", args=[translation.pk]), follow=True)
        self._assert_hook_blocked(response, reverse("wagtailadmin_pages:edit", args=[translation.pk]))

    def test_delete_allowed_when_neither_page_nor_translation_published(self):
        page = InformationPageFactory(parent=self.index_page, live=False)
        page.first_published_at = None
        page.last_published_at = None
        page.save(update_fields=["first_published_at", "last_published_at"])

        welsh_locale = Locale.objects.get(language_code="cy")
        self.index_page.copy_for_translation(welsh_locale, alias=True)
        translation = page.copy_for_translation(welsh_locale)
        translation.first_published_at = None
        translation.last_published_at = None
        translation.save(update_fields=["first_published_at", "last_published_at"])

        response = self.client.get(reverse("wagtailadmin_pages:delete", args=[translation.pk]))
        self.assertEqual(response.status_code, 200)


class BulkDeleteAsPublishingOfficerTests(WagtailTestUtils, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.officer = UserFactory(access_admin=True, username="officer_bulk_delete")
        cls.officer.groups.add(Group.objects.get(name=settings.PUBLISHING_OFFICERS_GROUP_NAME))
        cls.root_index = IndexPageFactory()

    def setUp(self):
        self.client.force_login(self.officer)

    @staticmethod
    def _make_never_published(parent):
        child = InformationPageFactory(parent=parent, live=False)
        child.first_published_at = None
        child.last_published_at = None
        child.save(update_fields=["first_published_at", "last_published_at"])
        return child

    def test_officer_can_bulk_delete_never_published_subtree(self):
        parent = self._make_never_published(self.root_index)
        child = self._make_never_published(parent)

        response = self.client.post(reverse("wagtailadmin_pages:delete", args=[parent.pk]), follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(InformationPage.objects.filter(pk=parent.pk).exists())
        self.assertFalse(InformationPage.objects.filter(pk=child.pk).exists())

    def test_officer_cannot_bulk_delete_subtree_with_previously_published_descendant(self):
        parent = self._make_never_published(self.root_index)
        published_child = InformationPageFactory(
            parent=parent,
            first_published_at=timezone.now() - timedelta(days=2),
            last_published_at=timezone.now() - timedelta(days=1),
        )

        edit_url = reverse("wagtailadmin_pages:edit", args=[parent.pk])
        response = self.client.post(reverse("wagtailadmin_pages:delete", args=[parent.pk]), follow=True)

        self.assertRedirects(response, edit_url)
        messages = [msg.message.strip() for msg in response.context["messages"]]
        self.assertTrue(
            any("published previously" in msg for msg in messages),
            f"Expected 'published previously' warning, got: {messages}",
        )
        # Neither the parent nor the previously-published child should have been deleted
        self.assertTrue(InformationPage.objects.filter(pk=parent.pk).exists())
        self.assertTrue(InformationPage.objects.filter(pk=published_child.pk).exists())


class BulkActionDeleteHookTests(WagtailTestUtils, TestCase):
    """The Wagtail multi-select bulk-delete action bypasses `before_delete_page`, so the
    `before_bulk_action` hook must enforce the same rule.
    """

    @classmethod
    def setUpTestData(cls):
        cls.superuser = cls.create_superuser("admin_bulk")
        cls.index_page = IndexPageFactory()

    def setUp(self):
        self.client.force_login(self.superuser)

    @staticmethod
    def _bulk_delete_url(page_ids, next_url="/admin/"):
        base = reverse("wagtail_bulk_action", args=("wagtailcore", "page", "delete"))
        query = "&".join(f"id={pid}" for pid in page_ids)
        return f"{base}?{query}&next={next_url}"

    @staticmethod
    def _make_never_published(parent):
        page = InformationPageFactory(parent=parent, live=False)
        page.first_published_at = None
        page.last_published_at = None
        page.save(update_fields=["first_published_at", "last_published_at"])
        return page

    def test_bulk_delete_blocked_when_any_selected_page_was_previously_published(self):
        never_published = self._make_never_published(self.index_page)
        previously_published = InformationPageFactory(
            parent=self.index_page,
            first_published_at=timezone.now() - timedelta(days=3),
            last_published_at=timezone.now() - timedelta(days=1),
        )

        url = self._bulk_delete_url([never_published.pk, previously_published.pk])
        response = self.client.post(url, {"confirm": "yes"}, follow=True)

        messages = [msg.message.strip() for msg in response.context["messages"]]
        self.assertTrue(
            any("published previously" in msg for msg in messages),
            f"Expected 'published previously' warning, got: {messages}",
        )
        # Both pages should still exist — we block the whole operation
        self.assertTrue(InformationPage.objects.filter(pk=never_published.pk).exists())
        self.assertTrue(InformationPage.objects.filter(pk=previously_published.pk).exists())

    def test_bulk_delete_allowed_when_all_pages_are_never_published(self):
        page_a = self._make_never_published(self.index_page)
        page_b = self._make_never_published(self.index_page)

        url = self._bulk_delete_url([page_a.pk, page_b.pk])
        response = self.client.post(url, {"confirm": "yes"}, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(InformationPage.objects.filter(pk=page_a.pk).exists())
        self.assertFalse(InformationPage.objects.filter(pk=page_b.pk).exists())

    def test_bulk_delete_blocked_when_selected_page_has_previously_published_descendant(self):
        parent = self._make_never_published(self.index_page)
        InformationPageFactory(
            parent=parent,
            first_published_at=timezone.now() - timedelta(days=2),
            last_published_at=timezone.now() - timedelta(days=1),
        )
        sibling = self._make_never_published(self.index_page)

        url = self._bulk_delete_url([parent.pk, sibling.pk])
        response = self.client.post(url, {"confirm": "yes"}, follow=True)

        messages = [msg.message.strip() for msg in response.context["messages"]]
        self.assertTrue(any("published previously" in msg for msg in messages))
        self.assertTrue(InformationPage.objects.filter(pk=parent.pk).exists())
        self.assertTrue(InformationPage.objects.filter(pk=sibling.pk).exists())
