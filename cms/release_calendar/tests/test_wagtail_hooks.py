from django.test import TestCase
from django.urls import reverse
from wagtail.models import Page
from wagtail.test.utils import WagtailTestUtils

from cms.home.models import HomePage
from cms.release_calendar.models import ReleaseCalendarIndex
from cms.release_calendar.wagtail_hooks import pin_release_calendar_page
from cms.standard_pages.tests.factories import IndexPageFactory


class ReleaseCalendarHooksTestCase(WagtailTestUtils, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = cls.create_superuser(username="admin")
        cls.root = Page.get_first_root_node()
        cls.homepages = HomePage.objects.specific()
        cls.homepage = cls.homepages.first()
        cls.release_calendar_index = ReleaseCalendarIndex.objects.first()

    def setUp(self):
        self.login()

    def test_release_calendar_index_is_sorted_first(self):
        """Checks that the Release Calendar index page is placed before all other pages in the returned ordering."""
        IndexPageFactory(parent=self.homepage, title="New Index Page")
        pages = self.homepage.get_children().specific()
        result = pin_release_calendar_page(
            self.homepage,
            pages,
            None,
        )
        self.assertEqual(result[0], self.release_calendar_index)

    def test_release_calendar_index_is_first_in_explorer_page(self):
        """Checks that the Release Calendar index page is displayed at the top of the explorer page."""
        IndexPageFactory(parent=self.homepage, title="New Index Page")
        response = self.client.get(
            reverse(
                "wagtailadmin_explore",
                args=[self.homepage.id],
            )
        )
        pages = list(response.context["pages"])
        self.assertEqual(pages[0], self.release_calendar_index)

    def test_homepages_are_sorted_by_path(self):
        """Checks that home pages are ordered in ascending path order."""
        result = pin_release_calendar_page(self.root, self.homepages, None)
        paths = [homepage.path for homepage in result]
        self.assertEqual(paths, sorted(paths))
