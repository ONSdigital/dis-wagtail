from types import SimpleNamespace

from django.test import RequestFactory, TestCase
from django.urls import reverse
from wagtail.models import Page
from wagtail.test.utils import WagtailTestUtils

from cms.home.models import HomePage
from cms.release_calendar.models import ReleaseCalendarIndex
from cms.release_calendar.wagtail_hooks import pin_release_calendar_page
from cms.topics.tests.factories import TopicPageFactory


class ReleaseCalendarHooksTestCase(WagtailTestUtils, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.root = Page.get_first_root_node()
        cls.home_page = HomePage.objects.first()
        cls.release_calendar_index = ReleaseCalendarIndex.objects.first()
        cls.release_calendar_index.save_revision().publish()
        cls.request = RequestFactory().get("/")

        # Create two topic pages with initial revision timestamps
        cls.older_topic_page = TopicPageFactory(parent=cls.home_page, title="Older Topic")
        cls.older_topic_page.save_revision().publish()
        cls.newer_topic_page = TopicPageFactory(parent=cls.home_page, title="Newer Topic")
        cls.newer_topic_page.save_revision().publish()

    def test_release_calendar_index_is_sorted_first(self):
        """Unit test ensures the Release Calendar index page is returned first in the queryset by directly calling
        pin_release_calendar_page, verifying the ordering logic in isolation from Wagtail’s admin layer.
        """
        pages = self.home_page.get_children().specific()
        query = pin_release_calendar_page(self.home_page, pages, self.request)
        self.assertEqual(query.first(), self.release_calendar_index, "Release calendar index page is not first")

    def test_release_calendar_index_is_first_in_explorer_page(self):
        """Integration test ensures the Release Calendar index page appears first in the explorer page by
        validating the behaviour through Wagtail’s admin interface and confirming that the hook is invoked correctly.
        """
        self.login()

        # Update the older topic so it becomes the most recently modified page
        self.older_topic_page.title = "Older Topic Updated"
        self.older_topic_page.save_revision().publish()

        response = self.client.get(reverse("wagtailadmin_explore", args=[self.home_page.id]))
        pages = list(response.context["pages"])

        self.assertEqual(pages[0], self.release_calendar_index, "Release calendar index page is not first in explorer")
        self.assertEqual(pages[1], self.older_topic_page, "Updated topic page is not second in explorer")
        self.assertEqual(pages[2], self.newer_topic_page, "Topic page is not ordered by recency as expected")

    def test_sidebar_is_not_reordered(self):
        """Unit test ensures sidebar pages retain their original path order by calling pin_release_calendar_page
        directly with a simulated sidebar request and verifying that the function returns the queryset unchanged.
        """
        self.login()

        parent = self.home_page
        children = parent.get_children()

        # Simulate a sidebar request
        sidebar_request = self.client.get(f"/admin/api/pages/?child_of={parent.id}").wsgi_request

        # Set resolver_match with the view_name and child_of values that mimic the routing metadata of a real sidebar
        # listing request, allowing pin_release_calendar_page to recognise it as an admin sidebar call.
        sidebar_request.resolver_match = SimpleNamespace(
            view_name="wagtailadmin_api:pages:listing",
            kwargs={"child_of": parent.id},
        )

        result = pin_release_calendar_page(parent, children, sidebar_request)

        self.assertEqual(list(result), list(children), "Sidebar pages are not ordered by path")
