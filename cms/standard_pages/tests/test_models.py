from django.test import TestCase
from wagtail.test.utils import WagtailTestUtils

from cms.standard_pages.tests.factories import IndexPageFactory, InformationPageFactory


class IndexPageTestCase(WagtailTestUtils, TestCase):
    """Test IndexPage model properties and methods."""

    def setUp(self):
        self.page = IndexPageFactory(
            title="Test Index Page",
            description="This is an example",
            content="This is the main content",
            featured_pages=None,
            related_links=None,
        )

        self.page_url = self.page.url

    def test_no_featured_pages_displayed_when_no_children_and_no_custom_featured_pages_selected(self):
        """Test that the Featured Items block isn't displayed when the Index Page has no child pages
        and no custom Featured Items are specified.
        """
        self.page.featured_pages = None

        response = self.client.get(self.page_url)
        self.page.save_revision().publish()

        self.assertEqual(response.status_code, 200)

        self.assertNotContains(response, "ons-document-list")

    def test_children_displayed_as_featured_pages_when_no_custom_featured_pages(self):
        """Test that the children pages of the Index Page are displayed
        when no custom Featured Items are specified.
        """
        child_page = InformationPageFactory(parent=self.page)

        self.page.save_revision().publish()

        response = self.client.get(self.page_url)

        self.assertEqual(response.status_code, 200)

        featured_page_html = f"""
            <ul class="ons-document-list">
            <li class="ons-document-list__item ons-document-list__item--featured">
                <div class="ons-document-list__item-content">
                    <div class="ons-document-list__item-header">
                        <h2 class="ons-document-list__item-title ons-u-fs-m ons-u-mt-no ons-u-mb-2xs">
                        <a href="{child_page.url}">{child_page.title}</a>
                        </h2>
                    </div>
                </div>
            </li>
            </ul>
        """
        self.assertContains(response, featured_page_html, html=True)

    def test_custom_featured_page_external_page_is_displayed_correctly(self):
        """Test that the custom featured items are displayed on the page."""
        featured_page_dict = {
            "type": "featured_page",
            "value": {
                "title": "Title of the custom featured item",
                "description": "Description of the custom featured item",
                "external_url": "external-url.com",
            },
        }

        self.page.featured_pages = [featured_page_dict]
        self.page.save_revision().publish()

        response = self.client.get(self.page_url)

        self.assertEqual(response.status_code, 200)
        featured_page_html = f"""
            <ul class="ons-document-list">
            <li class="ons-document-list__item ons-document-list__item--featured">
                <div class="ons-document-list__item-content">
                    <div class="ons-document-list__item-header">
                        <h2 class="ons-document-list__item-title ons-u-fs-m ons-u-mt-no ons-u-mb-2xs">
                        <a href="{featured_page_dict['value']['external_url']}">
                            {featured_page_dict['value']['title']}
                        </a>
                        </h2>
                    </div>
                    <div class="ons-document-list__item-description">{featured_page_dict['value']['description']}</div>
                </div>
            </li>
            </ul>
        """
        self.assertContains(response, featured_page_html, html=True)

    def test_custom_featured_page_internal_page_is_displayed_correctly(self):
        """Test that the custom featured items are displayed on the page."""
        internal_page = InformationPageFactory(parent=self.page)

        featured_page_dict = {
            "type": "featured_page",
            "value": {"page": internal_page.id},
        }

        self.page.featured_pages = [featured_page_dict]
        self.page.save_revision().publish()

        response = self.client.get(self.page_url)

        self.assertEqual(response.status_code, 200)

        featured_page_html = f"""
            <ul class="ons-document-list">
            <li class="ons-document-list__item ons-document-list__item--featured">
                <div class="ons-document-list__item-content">
                    <div class="ons-document-list__item-header">
                        <h2 class="ons-document-list__item-title ons-u-fs-m ons-u-mt-no ons-u-mb-2xs">
                        <a href="{internal_page.url}">
                            {internal_page.title}
                        </a>
                        </h2>
                    </div>
                </div>
            </li>
            </ul>
        """
        self.assertContains(response, featured_page_html, html=True)

    def test_get_formatted_related_links_list_works_for_internal_pages(self):
        """Test that the links to internal pages rare returned
        in a format that can be consumed by the Design System list component.
        """
        internal_page = InformationPageFactory(parent=self.page)

        self.page.related_links = [{"type": "related_link", "value": {"page": internal_page.id}}]

        formatted_related_links = self.page.get_formatted_related_links_list()

        self.assertEqual(formatted_related_links, [{"title": internal_page.title, "url": internal_page.url}])

    def test_get_formatted_related_links_list_works_for_external_pages(self):
        """Test that the links to external pages are returned
        in a format that can be consumed by the Design System list component.
        """
        self.page.related_links = [
            {"type": "related_link", "value": {"title": "An external page", "external_url": "external-url.com"}}
        ]

        formatted_related_links = self.page.get_formatted_related_links_list()

        self.assertEqual(formatted_related_links, [{"title": "An external page", "url": "external-url.com"}])
