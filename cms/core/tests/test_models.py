from django.conf import settings
from django.test import TestCase
from django.urls import reverse
from wagtail.coreutils import get_dummy_request
from wagtail.test.utils.wagtail_tests import WagtailTestUtils

from cms.articles.tests.factories import ArticleSeriesPageFactory, StatisticalArticlePageFactory
from cms.core.models import ContactDetails
from cms.standard_pages.tests.factories import InformationPageFactory


class ContactDetailsTestCase(WagtailTestUtils, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.contact = ContactDetails.objects.create(name="PSF", email="psf@ons.gov.uk")

    def test_contactdetails__str(self):
        self.assertEqual(str(self.contact), "PSF")

    def test_contactdetails_trims_trailing_whitespace_on_save(self):
        details = ContactDetails(name=" Retail ", email="retail@ons.gov.uk")
        details.save()

        self.assertEqual(details.name, "Retail")

    def test_contactdetails_creation(self):
        self.assertEqual(ContactDetails.objects.count(), 1)
        ContactDetails.objects.create(name="PSF", email="psf.extra@ons.gov.uk")

        self.assertEqual(ContactDetails.objects.count(), 2)

    def test_contactdetails_add_via_ui(self):
        self.login()
        response = self.client.post(
            reverse(ContactDetails.snippet_viewset.get_url_name("add")),  # pylint: disable=no-member
            data={"name": self.contact.name, "email": self.contact.email},
        )

        self.assertContains(response, "Contact details with this name and email combination already exists.")
        self.assertEqual(ContactDetails.objects.count(), 1)


class PageBreadcrumbsTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.series = ArticleSeriesPageFactory()
        cls.statistical_article = StatisticalArticlePageFactory(parent=cls.series)

    def setUp(self):
        self.mock_request = get_dummy_request()

    def test_breadcrumbs_output_format(self):
        """Test that get_breadcrumbs correctly outputs the parent pages in the correct format."""
        breadcrumbs_output = self.statistical_article.get_breadcrumbs(request=self.mock_request)

        series_parent = self.series.get_parent()

        expected_entries = [
            {
                "url": "/",
                "text": "Home",
            },
            {
                "url": series_parent.get_parent().get_url(),
                "text": series_parent.get_parent().title,
            },
            {
                "url": series_parent.get_url(),
                "text": series_parent.title,
            },
        ]

        self.assertIsInstance(breadcrumbs_output, list)
        self.assertEqual(len(breadcrumbs_output), 3)
        self.assertListEqual(breadcrumbs_output, expected_entries)

    def test_breadcrumbs_include_self(self):
        """Test that get_breadcrumbs includes the page when request includes `breadcrumbs_include_self` attribute."""
        self.mock_request.breadcrumbs_include_self = True
        breadcrumbs_output = self.statistical_article.get_breadcrumbs(request=self.mock_request)

        series_parent = self.series.get_parent()

        expected_entries = [
            {
                "url": "/",
                "text": "Home",
            },
            {
                "url": series_parent.get_parent().get_url(),
                "text": series_parent.get_parent().title,
            },
            {
                "url": series_parent.get_url(),
                "text": series_parent.title,
            },
            {
                "url": self.statistical_article.get_url(),
                "text": self.statistical_article.title,
            },
        ]

        self.assertIsInstance(breadcrumbs_output, list)
        self.assertEqual(len(breadcrumbs_output), 4)
        self.assertListEqual(breadcrumbs_output, expected_entries)


class CanonicalFullUrlsTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.information_page = InformationPageFactory()

    def setUp(self):
        self.mock_request = get_dummy_request()

    def test_canonical_full_url(self):
        """Test that get_canonical_url returns the correct full URL for a page, including base URL."""
        canonical_url = self.information_page.get_canonical_full_url(self.mock_request)

        self.assertEqual(
            canonical_url, settings.WAGTAILADMIN_BASE_URL + self.information_page.get_url(self.mock_request)
        )
