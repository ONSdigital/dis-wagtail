from django.core.cache import cache
from django.test import TestCase, override_settings
from wagtail.models import PageLogEntry
from wagtail.test.utils import WagtailTestUtils

from cms.articles.tests.factories import StatisticalArticlePageFactory


@override_settings(CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}})
class BasePageEditSaveAuditLogTestCase(WagtailTestUtils, TestCase):
    """Tests for BasePage.save_revision cooldown on the "wagtail.edit" audit log entry."""

    @classmethod
    def setUpTestData(cls) -> None:
        cls.superuser = cls.create_superuser(username="admin")
        cls.other_user = cls.create_superuser(username="other_admin")
        cls.page = StatisticalArticlePageFactory(title="Test Article")

    def setUp(self) -> None:
        cache.clear()
        PageLogEntry.objects.filter(page_id=self.page.pk, action="wagtail.edit").delete()

    def _edit_count(self, *, page_id: int | None = None) -> int:
        return PageLogEntry.objects.filter(page_id=page_id or self.page.pk, action="wagtail.edit").count()

    def test_save_revision_creates_audit_log_entry(self) -> None:
        self.page.save_revision(user=self.superuser, log_action=True)

        self.assertEqual(self._edit_count(), 1)

    def test_save_revision_without_log_action_does_not_log(self) -> None:
        self.page.save_revision(user=self.superuser)

        self.assertEqual(self._edit_count(), 0)

    def test_save_revision_cooldown_prevents_duplicate_entries(self) -> None:
        """Repeated saves within the cooldown (e.g. autosave) should only log once."""
        self.page.save_revision(user=self.superuser, log_action=True)
        self.assertEqual(self._edit_count(), 1)

        self.page.save_revision(user=self.superuser, log_action=True)
        self.assertEqual(self._edit_count(), 1)

        self.page.save_revision(user=self.superuser, log_action=True)
        self.assertEqual(self._edit_count(), 1)

    def test_save_revision_cooldown_allows_new_entry_after_expiry(self) -> None:
        self.page.save_revision(user=self.superuser, log_action=True)
        self.assertEqual(self._edit_count(), 1)

        # Simulate cooldown expiry by clearing the cache
        cache.clear()

        self.page.save_revision(user=self.superuser, log_action=True)
        self.assertEqual(self._edit_count(), 2)

    def test_save_revision_different_users_get_separate_cooldowns(self) -> None:
        self.page.save_revision(user=self.superuser, log_action=True)
        self.page.save_revision(user=self.other_user, log_action=True)

        log_entries = PageLogEntry.objects.filter(page_id=self.page.pk, action="wagtail.edit")
        self.assertEqual(log_entries.count(), 2)

        users = set(log_entries.values_list("user_id", flat=True))
        self.assertEqual(users, {self.superuser.pk, self.other_user.pk})

    def test_save_revision_different_pages_get_separate_cooldowns(self) -> None:
        other_page = StatisticalArticlePageFactory(title="Other Article")
        PageLogEntry.objects.filter(action="wagtail.edit").delete()

        self.page.save_revision(user=self.superuser, log_action=True)
        other_page.save_revision(user=self.superuser, log_action=True)

        log_entries = PageLogEntry.objects.filter(action="wagtail.edit")
        self.assertEqual(log_entries.count(), 2)

        page_ids = set(log_entries.values_list("page_id", flat=True))
        self.assertEqual(page_ids, {self.page.pk, other_page.pk})

    def test_save_revision_reverting_is_not_subject_to_cooldown(self) -> None:
        """Reverting to a previous revision is a deliberate action and should always be logged."""
        first_revision = self.page.save_revision(user=self.superuser, log_action=True)
        self.assertEqual(self._edit_count(), 1)

        PageLogEntry.objects.filter(page_id=self.page.pk, action="wagtail.revert").delete()

        self.page.save_revision(user=self.superuser, log_action=True, previous_revision=first_revision)
        self.page.save_revision(user=self.superuser, log_action=True, previous_revision=first_revision)

        revert_count = PageLogEntry.objects.filter(page_id=self.page.pk, action="wagtail.revert").count()
        self.assertEqual(revert_count, 2)
