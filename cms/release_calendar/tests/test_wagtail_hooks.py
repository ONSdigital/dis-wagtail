from django.test import RequestFactory, TestCase
from django.urls import reverse
from wagtail.models import Page
from wagtail.test.utils import WagtailTestUtils

from cms.home.models import HomePage
from cms.release_calendar.models import ReleaseCalendarIndex
from cms.release_calendar.wagtail_hooks import pin_release_calendar_page
from cms.standard_pages.tests.factories import IndexPageFactory
from cms.topics.tests.factories import TopicPageFactory


class ReleaseCalendarHooksTestCase(WagtailTestUtils, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.root = Page.get_first_root_node()
        cls.homepage = HomePage.objects.first()
        cls.release_calendar_index = ReleaseCalendarIndex.objects.first()
        cls.release_calendar_index.save_revision().publish()
        cls.request = RequestFactory().get("/")
        cls.index_page = IndexPageFactory(parent=cls.homepage, title="Index Page")
        cls.index_page.save_revision().publish()

    def test_release_calendar_index_is_sorted_first(self):
        """Checks that the Release Calendar index page is placed before all other pages in the returned ordering."""
        pages = self.homepage.get_children().specific()
        query = pin_release_calendar_page(self.homepage, pages, self.request)
        self.assertEqual(query.first(), self.release_calendar_index, "Release calendar index page is not first")

    def test_release_calendar_index_is_first_in_explorer_page(self):
        """Checks that the Release Calendar index page is displayed at the top of the explorer page."""
        self.login()

        # Create two topic pages with initial revision timestamps
        older_topic = TopicPageFactory(parent=self.homepage, title="Older Topic")
        older_topic.save_revision().publish()

        newer_topic = TopicPageFactory(parent=self.homepage, title="Newer Topic")
        newer_topic.save_revision().publish()

        # Update the older topic so it becomes the most recently modified page
        older_topic.title = "Older Topic Updated"
        older_topic.save_revision().publish()

        response = self.client.get(reverse("wagtailadmin_explore", args=[self.homepage.id]))
        pages = list(response.context["pages"])

        self.assertEqual(pages[0], self.release_calendar_index, "Release calendar index page is not first in explorer")
        self.assertEqual(pages[1], older_topic, "Updated topic page is not second in explorer")
        self.assertEqual(pages[2], newer_topic, "Topic page is not ordered by recency as expected")
