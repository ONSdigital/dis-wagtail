from types import SimpleNamespace

from django.test import RequestFactory, SimpleTestCase, TestCase
from django.urls import reverse
from wagtail.models import Page
from wagtail.test.utils import WagtailTestUtils

from cms.home.models import HomePage
from cms.release_calendar.models import ReleaseCalendarIndex
from cms.release_calendar.wagtail_hooks import _explorer_has_active_query, pin_release_calendar_page
from cms.topics.tests.factories import TopicPageFactory

# Mirrors the empty query params Wagtail keeps on the results view after filters are cleared.
CLEARED_FILTER_QUERY = {
    "q": "",
    "latest_revision_created_at_from": "",
    "latest_revision_created_at_to": "",
    "has_child_pages": "",
    "locale": "",
}


class ExplorerHasActiveQueryTests(SimpleTestCase):
    def test_explorer_has_active_query_returns_false_for_blank_values(self):
        """Blank explorer query values should not count as active query state."""
        request = RequestFactory().get("/", CLEARED_FILTER_QUERY)

        self.assertFalse(_explorer_has_active_query(request))

    def test_explorer_has_active_query_ignores_fragment_refresh_and_pagination(self):
        """Wagtail fragment refresh and pagination params should not count as active query state."""
        request = RequestFactory().get("/", {"_w_filter_fragment": "1", "p": "2"})

        self.assertFalse(_explorer_has_active_query(request))

    def test_explorer_has_active_query_returns_true_for_non_empty_value(self):
        """Any non-empty user query value should count as active query state."""
        request = RequestFactory().get("/", {"content_type": "63"})

        self.assertTrue(_explorer_has_active_query(request))


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

    def setUp(self):
        self.login()

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
        # Update the older topic so it becomes the most recently modified page
        self.older_topic_page.title = "Older Topic Updated"
        self.older_topic_page.save_revision().publish()

        response = self.client.get(reverse("wagtailadmin_explore", args=[self.home_page.id]))
        pages = list(response.context["pages"])

        self.assertEqual(pages[0], self.release_calendar_index, "Release calendar index page is not first in explorer")
        self.assertEqual(pages[1], self.older_topic_page, "Updated topic page is not second in explorer")
        self.assertEqual(pages[2], self.newer_topic_page, "Topic page is not ordered by recency as expected")

    def test_release_calendar_index_is_not_first_in_explorer_results_with_active_filter(self):
        """Explorer results with an active filter should use Wagtail's default ordering."""
        response = self.client.get(
            reverse("wagtailadmin_explore_results", args=[self.home_page.id]),
            {
                "content_type": [
                    str(self.release_calendar_index.content_type_id),
                    str(self.older_topic_page.content_type_id),
                ]
            },
        )
        pages = list(response.context["pages"])

        # Expect pages to be orderded by most recently updated
        expected_page_order = [self.newer_topic_page, self.older_topic_page, self.release_calendar_index]

        self.assertEqual(
            pages, expected_page_order, "Release calendar index page should not be pinned in filtered results"
        )

    def test_release_calendar_index_is_first_in_explorer_results_after_filter_is_cleared(self):
        """Explorer results with only blank filter values should pin the release calendar again."""
        response = self.client.get(
            reverse("wagtailadmin_explore_results", args=[self.home_page.id]),
            CLEARED_FILTER_QUERY,
        )
        pages = list(response.context["pages"])

        self.assertEqual(
            pages[0],
            self.release_calendar_index,
            "Release calendar index page is not first after the filter is cleared",
        )

    def test_release_calendar_index_is_not_first_in_explorer_page_with_default_ordering_param(self):
        """Explorer requests that carry an explicit default ordering should not pin the calendar index."""
        response = self.client.get(
            reverse("wagtailadmin_explore", args=[self.home_page.id]),
            {"ordering": self.home_page.get_admin_default_ordering()},
        )
        pages = list(response.context["pages"])

        self.assertNotEqual(pages[0], self.release_calendar_index, "Explicit ordering should not be overridden")

    def test_sidebar_is_not_reordered(self):
        """Unit test ensures sidebar pages retain their original path order by calling pin_release_calendar_page
        directly with a simulated sidebar request and verifying that the function returns the queryset unchanged.
        """
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
