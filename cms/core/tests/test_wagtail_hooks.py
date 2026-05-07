from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from wagtail.models import Locale
from wagtail.test.utils import WagtailTestUtils

from cms.standard_pages.models import InformationPage
from cms.standard_pages.tests.factories import IndexPageFactory, InformationPageFactory
from cms.users.tests.factories import UserFactory


class PreventDeleteOfPreviouslyPublishedPageHookTests(WagtailTestUtils, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = cls.create_superuser("admin")
        cls.index_page = IndexPageFactory()

    def setUp(self):
        self.client.force_login(self.superuser)

    def _assert_hook_blocked(self, response, edit_url):
        self.assertRedirects(response, edit_url)
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
