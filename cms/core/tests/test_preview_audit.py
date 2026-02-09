from typing import Any
from unittest.mock import patch

from django.contrib.auth.models import AnonymousUser
from django.core.cache import cache
from django.test import RequestFactory, TestCase, override_settings
from wagtail.models import PageLogEntry
from wagtail.test.utils import WagtailTestUtils

from cms.articles.tests.factories import StatisticalArticlePageFactory


class BasePagePreviewAuditLogTestCase(WagtailTestUtils, TestCase):
    """Tests for BasePage._log_preview method and preview audit logging."""

    @classmethod
    def setUpTestData(cls) -> None:
        cls.superuser = cls.create_superuser(username="admin")
        cls.other_user = cls.create_superuser(username="other_admin")
        cls.page = StatisticalArticlePageFactory(title="Test Article")
        cls.factory = RequestFactory()

    def test_log_preview_creates_audit_log_entry(self) -> None:
        """Test that _log_preview creates an audit log entry."""
        PageLogEntry.objects.filter(page_id=self.page.pk, action="pages.preview_mode_used").delete()

        request = self.factory.get("/")
        request.user = self.superuser

        self.page._log_preview(request, "default")  # pylint: disable=protected-access

        log_entry = PageLogEntry.objects.filter(page_id=self.page.pk, action="pages.preview_mode_used").first()
        self.assertIsNotNone(log_entry)
        self.assertEqual(log_entry.user, self.superuser)
        self.assertEqual(log_entry.data.get("preview_mode"), "default")

    def test_log_preview_handles_unauthenticated_user(self) -> None:
        """Test that _log_preview handles unauthenticated users."""
        # Edge case: ensure no error occurs and log entry is created with no user.
        # This is unlikely in practice since previewing requires authentication.
        PageLogEntry.objects.filter(page_id=self.page.pk, action="pages.preview_mode_used").delete()

        request = self.factory.get("/")
        request.user = AnonymousUser()

        self.page._log_preview(request, "default")  # pylint: disable=protected-access

        log_entry = PageLogEntry.objects.filter(page_id=self.page.pk, action="pages.preview_mode_used").first()
        self.assertIsNotNone(log_entry)
        self.assertIsNone(log_entry.user)

    @override_settings(CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}})
    def test_log_preview_cooldown_prevents_duplicate_entries(self) -> None:
        """Test that previewing the same mode multiple times within the cooldown period
        only creates one audit log entry.
        """
        cache.clear()
        PageLogEntry.objects.filter(page_id=self.page.pk, action="pages.preview_mode_used").delete()

        request = self.factory.get("/")
        request.user = self.superuser

        # First preview - should create a log entry
        self.page._log_preview(request, "default")  # pylint: disable=protected-access
        first_count = PageLogEntry.objects.filter(page_id=self.page.pk, action="pages.preview_mode_used").count()
        self.assertEqual(first_count, 1)

        # Second preview within cooldown - should NOT create another log entry
        self.page._log_preview(request, "default")  # pylint: disable=protected-access
        second_count = PageLogEntry.objects.filter(page_id=self.page.pk, action="pages.preview_mode_used").count()
        self.assertEqual(second_count, 1)

        # Third preview within cooldown - still no new entry
        self.page._log_preview(request, "default")  # pylint: disable=protected-access
        third_count = PageLogEntry.objects.filter(page_id=self.page.pk, action="pages.preview_mode_used").count()
        self.assertEqual(third_count, 1)

    @override_settings(CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}})
    def test_log_preview_cooldown_allows_new_entry_after_expiry(self) -> None:
        """Test that a new audit log entry is created after the cooldown expires."""
        cache.clear()
        PageLogEntry.objects.filter(page_id=self.page.pk, action="pages.preview_mode_used").delete()

        request = self.factory.get("/")
        request.user = self.superuser

        # First preview
        self.page._log_preview(request, "default")  # pylint: disable=protected-access
        first_count = PageLogEntry.objects.filter(page_id=self.page.pk, action="pages.preview_mode_used").count()
        self.assertEqual(first_count, 1)

        # Clear cache to simulate cooldown expiry. We don't need to wait since we can rely on cache clearing.
        cache.clear()

        # Second preview after cooldown expiry - should create a new log entry
        self.page._log_preview(request, "default")  # pylint: disable=protected-access
        second_count = PageLogEntry.objects.filter(page_id=self.page.pk, action="pages.preview_mode_used").count()
        self.assertEqual(second_count, 2)

    @override_settings(CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}})
    def test_log_preview_different_users_get_separate_cooldowns(self) -> None:
        """Test that different users have separate cooldown periods."""
        cache.clear()
        PageLogEntry.objects.filter(page_id=self.page.pk, action="pages.preview_mode_used").delete()

        request = self.factory.get("/")
        request.user = self.superuser
        self.page._log_preview(request, "default")  # pylint: disable=protected-access

        # Second user previews the same page - should also create a log entry
        request.user = self.other_user
        self.page._log_preview(request, "default")  # pylint: disable=protected-access

        log_entries = PageLogEntry.objects.filter(page_id=self.page.pk, action="pages.preview_mode_used")
        self.assertEqual(log_entries.count(), 2)

        users = set(log_entries.values_list("user_id", flat=True))
        self.assertEqual(users, {self.superuser.pk, self.other_user.pk})

    @override_settings(CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}})
    def test_log_preview_different_modes_get_separate_cooldowns(self) -> None:
        """Test that different preview modes have separate cooldown periods for the same user."""
        cache.clear()
        PageLogEntry.objects.filter(page_id=self.page.pk, action="pages.preview_mode_used").delete()

        request = self.factory.get("/")
        request.user = self.superuser

        # Preview in default mode
        self.page._log_preview(request, "default")  # pylint: disable=protected-access

        # Preview in related_data mode - should also create a log entry
        self.page._log_preview(request, "related_data")  # pylint: disable=protected-access

        log_entries = PageLogEntry.objects.filter(page_id=self.page.pk, action="pages.preview_mode_used")
        self.assertEqual(log_entries.count(), 2)

        modes = {entry.data.get("preview_mode") for entry in log_entries}
        self.assertEqual(modes, {"default", "related_data"})

    @override_settings(CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}})
    def test_log_preview_different_pages_get_separate_cooldowns(self) -> None:
        """Test that different pages have separate cooldown periods for the same user."""
        cache.clear()
        other_page = StatisticalArticlePageFactory(title="Other Article")
        PageLogEntry.objects.filter(action="pages.preview_mode_used").delete()

        request = self.factory.get("/")
        request.user = self.superuser

        # Preview first page
        self.page._log_preview(request, "default")  # pylint: disable=protected-access

        # Preview second page - should also create a log entry
        other_page._log_preview(request, "default")  # pylint: disable=protected-access

        log_entries = PageLogEntry.objects.filter(action="pages.preview_mode_used")
        self.assertEqual(log_entries.count(), 2)

        page_ids = set(log_entries.values_list("page_id", flat=True))
        self.assertEqual(page_ids, {self.page.pk, other_page.pk})

    def test_log_preview_mirrors_to_stdout(self) -> None:
        """Test that preview audit log entry is mirrored to stdout."""
        request = self.factory.get("/")
        request.user = self.superuser

        with patch("cms.core.audit.audit_logger") as mock_logger:
            self.page._log_preview(request, "default")  # pylint: disable=protected-access

            # Verify audit logger was called
            mock_logger.info.assert_called_once()
            call_args: tuple[tuple[Any, ...], dict[str, Any]] = mock_logger.info.call_args
            assert call_args[0][0] == "Audit event: %s"
            assert call_args[0][1] == "pages.preview_mode_used"

            # Verify extra data
            extra: dict[str, Any] = call_args[1]["extra"]
            assert extra["event"] == "pages.preview_mode_used"
            assert extra["object_type"] == "statistical article page"
            assert extra["object_id"] == self.page.id
            assert extra["data"] == {"preview_mode": "default"}
            assert "timestamp" in extra

    def test_serve_preview_calls_log_preview(self) -> None:
        """Test that BasePage.serve_preview calls _log_preview."""
        request = self.factory.get("/")
        request.user = self.superuser

        with patch.object(self.page, "_log_preview") as mock_log_preview:
            # Call serve_preview on the page
            self.page.serve_preview(request, "default")

            # Verify _log_preview was called
            mock_log_preview.assert_called_once_with(request, "default")

    def test_log_preview_does_not_log_unsaved_pages(self) -> None:
        """Test that _log_preview returns early for unsaved pages (no primary key)."""
        # Create an unsaved page (not persisted to database)
        unsaved_page = StatisticalArticlePageFactory.build(title="Unsaved Article")
        self.assertIsNone(unsaved_page.pk)

        initial_count = PageLogEntry.objects.filter(action="pages.preview_mode_used").count()

        request = self.factory.get("/")
        request.user = self.superuser

        # Should not raise an exception and should return early
        unsaved_page._log_preview(request, "default")  # pylint: disable=protected-access

        # Verify no log entry was created
        final_count = PageLogEntry.objects.filter(action="pages.preview_mode_used").count()
        self.assertEqual(initial_count, final_count)
