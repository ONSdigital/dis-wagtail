from django.test import TestCase
from django.utils import timezone

from cms.articles.tests.factories import StatisticalArticlePageFactory
from cms.bundles.enums import BundleStatus
from cms.bundles.models import BundleTeam
from cms.bundles.tests.factories import BundleFactory, BundlePageFactory
from cms.release_calendar.tests.factories import ReleaseCalendarPageFactory
from cms.teams.models import Team
from cms.users.tests.factories import UserFactory
from cms.workflows.tests.utils import mark_page_as_ready_to_publish
from functional_tests.step_helpers.users import create_user


class BundleModelTestCase(TestCase):
    """Test Bundle model properties and methods."""

    def setUp(self):
        self.bundle = BundleFactory(name="The bundle")
        self.statistical_article = StatisticalArticlePageFactory(title="PSF")

    def test_str(self):
        self.assertEqual(str(self.bundle), self.bundle.name)

    def test_scheduled_publication_date__direct(self):
        now = timezone.now()
        self.bundle.publication_date = now
        self.assertEqual(self.bundle.scheduled_publication_date, now)

    def test_scheduled_publication_date__via_release(self):
        release_page = ReleaseCalendarPageFactory()
        self.bundle.release_calendar_page = release_page
        self.assertEqual(self.bundle.scheduled_publication_date, release_page.release_date)

    def test_can_be_approved__by_status_only(self):
        test_cases = [
            (BundleStatus.DRAFT, False),
            (BundleStatus.IN_REVIEW, True),
            (BundleStatus.APPROVED, False),
            (BundleStatus.PUBLISHED, False),
        ]

        for status, expected in test_cases:
            with self.subTest(status=status):
                self.bundle.status = status
                self.assertEqual(self.bundle.can_be_approved, expected)

    def test_can_be_approved__with_pages(self):
        BundlePageFactory(parent=self.bundle, page=self.statistical_article)

        self.bundle.status = BundleStatus.IN_REVIEW
        self.assertFalse(self.bundle.can_be_approved)

        mark_page_as_ready_to_publish(self.statistical_article, UserFactory())
        self.assertTrue(self.bundle.can_be_approved)

    def test_get_bundled_pages(self):
        """Test get_bundled_pages returns correct queryset."""
        BundlePageFactory(parent=self.bundle, page=self.statistical_article)
        page_ids = self.bundle.get_bundled_pages().values_list("pk", flat=True)
        self.assertEqual(len(page_ids), 1)
        self.assertEqual(page_ids[0], self.statistical_article.pk)

    def test_bundlepage_orderable_str(self):
        bundle_page = BundlePageFactory(parent=self.bundle, page=self.statistical_article)

        self.assertEqual(str(bundle_page), f"BundlePage: page {self.statistical_article.pk} in bundle {self.bundle.id}")

    def test_active_teams(self):
        team = Team.objects.create(identifier="foo", name="Active team")
        inactive_team = Team.objects.create(identifier="inactive", name="Inactive team", is_active=False)

        BundleTeam.objects.create(parent=self.bundle, team=team)
        BundleTeam.objects.create(parent=self.bundle, team=inactive_team)

        self.assertListEqual(self.bundle.active_team_ids, [team.pk])

class BundelesCreatedbyTestCase(TestCase):
    """Test Bundle model properties and methods."""

    def setUp(self):
        self.publishing_officer = UserFactory(username="publishing_officer")
        self.bundle = BundleFactory(name="The bundle", created_by=self.publishing_officer)
        self.statistical_article = StatisticalArticlePageFactory(title="PSF")

    def test_str(self):
        self.assertEqual(str(self.publishing_officer), str(self.bundle.created_by))



class BundledPageMixinTestCase(TestCase):
    """Test BundledPageMixin properties and methods."""

    def setUp(self):
        self.page = StatisticalArticlePageFactory()
        self.bundle = BundleFactory()
        self.bundle_page = BundlePageFactory(parent=self.bundle, page=self.page)

    def test_bundles_property(self):
        self.assertEqual(self.page.bundles.count(), 1)
        self.assertEqual(self.page.bundles.first(), self.bundle)

    def test_active_bundles_property(self):
        self.bundle.status = BundleStatus.PUBLISHED
        self.bundle.save(update_fields=["status"])

        self.assertEqual(self.page.active_bundles.count(), 0)

        self.bundle.status = BundleStatus.DRAFT
        self.bundle.save(update_fields=["status"])

        self.assertEqual(self.page.active_bundles.count(), 1)

    def test_in_active_bundle_property(self):
        self.assertTrue(self.page.in_active_bundle)

        self.bundle.status = BundleStatus.PUBLISHED
        self.bundle.save(update_fields=["status"])

        del self.page.in_active_bundle  # clear the cached property
        del self.page.active_bundle  # clear the cached property
        self.assertFalse(self.page.in_active_bundle)

    def test_active_bundle_property(self):
        self.assertEqual(self.page.active_bundle, self.bundle)

        self.bundle.status = BundleStatus.PUBLISHED
        self.bundle.save(update_fields=["status"])

        del self.page.active_bundle  # cleared cached property
        self.assertIsNone(self.page.active_bundle)
