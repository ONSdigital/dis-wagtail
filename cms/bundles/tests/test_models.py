from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from cms.analysis.tests.factories import AnalysisPageFactory
from cms.bundles.enums import BundleStatus
from cms.bundles.tests.factories import BundleFactory, BundlePageFactory
from cms.release_calendar.tests.factories import ReleaseCalendarPageFactory


class BundleModelTestCase(TestCase):
    """Test Bundle model properties and methods."""

    def setUp(self):
        self.bundle = BundleFactory(name="The bundle")
        self.analysis_page = AnalysisPageFactory(title="PSF")

    def test_str(self):
        """Test string representation."""
        self.assertEqual(str(self.bundle), self.bundle.name)

    def test_scheduled_publication_date__direct(self):
        """Test scheduled_publication_date returns direct publication date."""
        del self.bundle.scheduled_publication_date  # clear the cached property
        now = timezone.now()
        self.bundle.publication_date = now
        self.assertEqual(self.bundle.scheduled_publication_date, now)

    def test_scheduled_publication_date__via_release(self):
        """Test scheduled_publication_date returns release calendar date."""
        release_page = ReleaseCalendarPageFactory()
        self.bundle.release_calendar_page = release_page
        self.assertEqual(self.bundle.scheduled_publication_date, release_page.release_date)

    def test_can_be_approved(self):
        """Test can_be_approved property."""
        test_cases = [
            (BundleStatus.PENDING, True),
            (BundleStatus.IN_REVIEW, True),
            (BundleStatus.APPROVED, False),
            (BundleStatus.RELEASED, False),
        ]

        for status, expected in test_cases:
            with self.subTest(status=status):
                self.bundle.status = status
                self.assertEqual(self.bundle.can_be_approved, expected)

    def test_get_bundled_pages(self):
        """Test get_bundled_pages returns correct queryset."""
        BundlePageFactory(parent=self.bundle, page=self.analysis_page)
        page_ids = self.bundle.get_bundled_pages().values_list("pk", flat=True)
        self.assertEqual(len(page_ids), 1)
        self.assertEqual(page_ids[0], self.analysis_page.pk)

    def test_save_updates_page_publication_dates(self):
        """Test save method updates page publication dates."""
        BundlePageFactory(parent=self.bundle, page=self.analysis_page)
        del self.bundle.scheduled_publication_date  # clear the cached property
        future_date = timezone.now() + timedelta(days=1)
        self.bundle.publication_date = future_date
        self.bundle.save()

        self.analysis_page.refresh_from_db()
        self.assertEqual(self.analysis_page.go_live_at, future_date)

    def test_save_doesnt_update_dates_when_released(self):
        """Test save method doesn't update dates for released bundles."""
        future_date = timezone.now() + timedelta(days=1)
        self.bundle.status = BundleStatus.RELEASED
        self.bundle.publication_date = future_date
        BundlePageFactory(parent=self.bundle, page=self.analysis_page)

        self.bundle.save()
        self.analysis_page.refresh_from_db()

        self.assertNotEqual(self.analysis_page.go_live_at, future_date)

    def test_bundlepage_orderable_str(self):
        """Checks the BundlePage model __str__ method."""
        bundle_page = BundlePageFactory(parent=self.bundle, page=self.analysis_page)

        self.assertEqual(str(bundle_page), f"BundlePage: page {self.analysis_page.pk} in bundle {self.bundle.id}")


class BundledPageMixinTestCase(TestCase):
    """Test BundledPageMixin properties and methods."""

    def setUp(self):
        self.page = AnalysisPageFactory()
        self.bundle = BundleFactory()
        self.bundle_page = BundlePageFactory(parent=self.bundle, page=self.page)

    def test_bundles_property(self):
        """Test bundles property returns correct queryset."""
        self.assertEqual(self.page.bundles.count(), 1)
        self.assertEqual(self.page.bundles.first(), self.bundle)

    def test_active_bundles_property(self):
        """Test active_bundles property returns correct queryset."""
        self.bundle.status = BundleStatus.RELEASED
        self.bundle.save(update_fields=["status"])

        self.assertEqual(self.page.active_bundles.count(), 0)

        self.bundle.status = BundleStatus.PENDING
        self.bundle.save(update_fields=["status"])

        self.assertEqual(self.page.active_bundles.count(), 1)

    def test_in_active_bundle_property(self):
        """Test in_active_bundle property."""
        self.assertTrue(self.page.in_active_bundle)

        self.bundle.status = BundleStatus.RELEASED
        self.bundle.save(update_fields=["status"])

        del self.page.in_active_bundle  # clear the cached property
        del self.page.active_bundle  # clear the cached property
        self.assertFalse(self.page.in_active_bundle)

    def test_active_bundle_property(self):
        """Test active_bundle property returns most recent active bundle."""
        self.assertEqual(self.page.active_bundle, self.bundle)

        self.bundle.status = BundleStatus.RELEASED
        self.bundle.save(update_fields=["status"])

        del self.page.active_bundle  # cleared cached property
        self.assertIsNone(self.page.active_bundle)
