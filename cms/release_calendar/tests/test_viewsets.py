from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from wagtail.models import GroupPagePermission, Locale
from wagtail.test.utils import WagtailTestUtils

from cms.bundles.tests.factories import BundleFactory
from cms.core.tests.utils import rebuild_internal_search_index
from cms.release_calendar.enums import ReleaseStatus
from cms.release_calendar.tests.factories import ReleaseCalendarPageFactory
from cms.release_calendar.viewsets import release_calendar_chooser_viewset
from cms.users.tests.factories import UserFactory


class TestFutureReleaseCalendarChooserViewSet(WagtailTestUtils, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = cls.create_superuser(username="admin")
        cls.chooser_url = release_calendar_chooser_viewset.widget_class().get_chooser_modal_url()

        tomorrow = timezone.now() + timedelta(days=1)
        cls.provisional = ReleaseCalendarPageFactory(
            title="Preliminary", status=ReleaseStatus.PROVISIONAL, release_date=tomorrow
        )
        cls.confirmed = ReleaseCalendarPageFactory(
            title="Acknowledged", status=ReleaseStatus.CONFIRMED, release_date=tomorrow
        )
        cls.cancelled = ReleaseCalendarPageFactory(
            title="Cancelled", status=ReleaseStatus.CANCELLED, release_date=tomorrow
        )
        cls.published = ReleaseCalendarPageFactory(
            title="Published", status=ReleaseStatus.PUBLISHED, release_date=tomorrow
        )

        cls.past = ReleaseCalendarPageFactory(
            title="Preliminary, but in the past",
            status=ReleaseStatus.PROVISIONAL,
            release_date=timezone.now() - timedelta(minutes=1),
        )

        cls.welsh_locale, _ = Locale.objects.get_or_create(language_code="cy")

    def setUp(self):
        self.client.force_login(self.superuser)

    def assert_only_provisional_or_confirmed_are_shown(self, response):
        self.assertContains(response, self.provisional.title)
        self.assertContains(response, ReleaseStatus.PROVISIONAL.label)
        self.assertContains(response, self.confirmed.title)
        self.assertContains(response, ReleaseStatus.CONFIRMED.label)
        self.assertNotContains(response, self.cancelled.title)
        self.assertNotContains(response, self.published.title)
        self.assertNotContains(response, self.past.title)

    def test_chooser_viewset(self):
        response = self.client.get(self.chooser_url)
        self.assert_only_provisional_or_confirmed_are_shown(response)

    def test_chooser_search(self):
        """Tests that the chooser search results work as expected."""
        rebuild_internal_search_index()
        chooser_results_url = reverse(release_calendar_chooser_viewset.get_url_name("choose_results"))
        response = self.client.get(f"{chooser_results_url}?q=preliminary")

        self.assertContains(response, self.provisional.title)
        self.assertContains(response, ReleaseStatus.PROVISIONAL.label)
        self.assertNotContains(response, self.confirmed.title)
        self.assertNotContains(response, ReleaseStatus.CONFIRMED.label)
        self.assertNotContains(response, self.cancelled.title)
        self.assertNotContains(response, self.published.title)
        self.assertNotContains(response, self.past.title)

    def test_chooser_excludes_release_calendar_pages_already_in_an_active_bundle(self):
        bundle = BundleFactory()
        bundle.release_calendar_page = self.provisional
        bundle.save(update_fields=["release_calendar_page"])

        response = self.client.get(self.chooser_url)

        self.assertContains(response, self.confirmed.title)
        self.assertNotContains(response, self.provisional.title)
        self.assertNotContains(response, self.cancelled.title)
        self.assertNotContains(response, self.published.title)
        self.assertNotContains(response, self.past.title)

    def test_chooser_excludes_aliases(self):
        provisional_alias = self.provisional.copy_for_translation(self.welsh_locale, copy_parents=True, alias=True)
        confirmed_alias = self.confirmed.create_alias(parent=self.confirmed.get_parent(), update_slug="confirmed-alias")

        response = self.client.get(self.chooser_url)

        # the chosen URL contains the page id
        chosen_url_name = release_calendar_chooser_viewset.get_url_name("chosen")
        self.assertNotContains(response, reverse(chosen_url_name, kwargs={"pk": provisional_alias.pk}))
        self.assertNotContains(response, reverse(chosen_url_name, kwargs={"pk": confirmed_alias.pk}))

    def test_chooser_only_includes_pages_the_given_user_has_access_to(self):
        def assert_cannot_see_pages(response):
            self.assertNotContains(response, self.provisional.title)
            self.assertNotContains(response, self.confirmed.title)
            self.assertNotContains(response, self.cancelled.title)
            self.assertNotContains(response, self.published.title)
            self.assertNotContains(response, self.past.title)
            self.assertContains(
                response,
                "There are no pending release calendar pages with a "
                "future release date that are not in an active bundle already.",
            )

        simple_user = UserFactory(username="viewer", access_admin=True)
        self.client.force_login(simple_user)

        response = self.client.get(self.chooser_url)
        assert_cannot_see_pages(response)

        viewer_group = Group.objects.get(name=settings.VIEWERS_GROUP_NAME)
        simple_user.groups.add(viewer_group)
        response = self.client.get(self.chooser_url)
        assert_cannot_see_pages(response)

        GroupPagePermission.objects.create(
            group=viewer_group,
            page=self.provisional.get_parent(),
            permission_type="add",
        )

        response = self.client.get(self.chooser_url)
        self.assert_only_provisional_or_confirmed_are_shown(response)

    def test_chooser__no_results(self):
        bundle = BundleFactory()
        bundle.release_calendar_page = self.provisional
        bundle.save(update_fields=["release_calendar_page"])

        self.confirmed.status = ReleaseStatus.PUBLISHED
        self.confirmed.save_revision().publish()

        response = self.client.get(self.chooser_url)
        self.assertContains(
            response,
            "There are no pending release calendar pages with a "
            "future release date that are not in an active bundle already.",
        )

    def test_choose__contains_locale_column(self):
        """Tests that the chooser view contains the locale column."""
        response = self.client.get(self.chooser_url)

        self.assertContains(response, "Locale")
        self.assertContains(response, "English")
