from django.conf import settings
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse
from wagtail.coreutils import get_dummy_request
from wagtail.test.utils.form_data import rich_text
from wagtail.test.utils.wagtail_tests import WagtailTestUtils

from cms.articles.tests.factories import ArticleSeriesPageFactory, StatisticalArticlePageFactory
from cms.core.models import ContactDetails, Definition
from cms.home.models import HomePage
from cms.standard_pages.tests.factories import InformationPageFactory
from cms.taxonomy.models import Topic
from cms.themes.tests.factories import ThemePageFactory
from cms.topics.tests.factories import TopicPageFactory
from cms.users.tests.factories import UserFactory


class ContactDetailsTestCase(WagtailTestUtils, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.contact = ContactDetails.objects.create(name="PSF", email="psf@ons.gov.uk")

        cls.publishing_admin = UserFactory(username="publishing_admin", access_admin=True)
        admin_group = Group.objects.get(name=settings.PUBLISHING_ADMINS_GROUP_NAME)
        admin_group.user_set.add(cls.publishing_admin)

        cls.publishing_officer = UserFactory(username="publishing_officer", access_admin=True)
        admin_group = Group.objects.get(name=settings.PUBLISHING_OFFICERS_GROUP_NAME)
        admin_group.user_set.add(cls.publishing_officer)

        cls.add_url = reverse(ContactDetails.snippet_viewset.get_url_name("add"))  # pylint: disable=no-member

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
        self.client.force_login(self.publishing_admin)
        response = self.client.post(
            self.add_url,
            data={"name": self.contact.name, "email": self.contact.email},
        )

        self.assertContains(response, "Contact details with this name and email combination already exists.")
        self.assertEqual(ContactDetails.objects.count(), 1)

    def test_publishing_admins_can_publish(self):
        self.client.force_login(self.publishing_admin)
        response = self.client.post(
            self.add_url,
            data={"name": "New contact", "email": "new@example.com", "action-publish": "action-publish"},
            follow=True,
        )
        self.assertContains(response, "Contact details &#x27;New contact&#x27; created and published.")
        self.assertEqual(ContactDetails.objects.count(), 2)
        self.assertTrue(ContactDetails.objects.last().live)

    def test_publishing_officer_cannot_access_the_add_page(self):
        self.client.force_login(self.publishing_officer)

        response = self.client.get(self.add_url, follow=True)
        self.assertContains(response, "Sorry, you do not have permission to access this area.")

    def test_publishing_officer_cannot_publish(self):
        self.client.force_login(self.publishing_officer)
        response = self.client.post(
            self.add_url,
            data={"name": "New contact", "email": "new@example.com", "action-publish": "action-publish"},
            follow=True,
        )
        self.assertContains(response, "Sorry, you do not have permission to access this area.")


class DefinitionTestCase(WagtailTestUtils, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.publishing_admin = UserFactory(username="publishing_admin", access_admin=True)
        admin_group = Group.objects.get(name=settings.PUBLISHING_ADMINS_GROUP_NAME)
        admin_group.user_set.add(cls.publishing_admin)

        cls.publishing_officer = UserFactory(username="publishing_officer", access_admin=True)
        admin_group = Group.objects.get(name=settings.PUBLISHING_OFFICERS_GROUP_NAME)
        admin_group.user_set.add(cls.publishing_officer)

        cls.add_url = reverse(Definition.snippet_viewset.get_url_name("add"))  # pylint: disable=no-member

    def test_publishing_officer_can_publish(self):
        self.client.force_login(self.publishing_admin)
        response = self.client.post(
            self.add_url,
            data={"name": "New definition", "definition": rich_text("definition"), "action-publish": "action-publish"},
            follow=True,
        )
        self.assertContains(response, "Definition &#x27;New definition&#x27; created and published.")
        self.assertEqual(Definition.objects.count(), 1)
        self.assertTrue(Definition.objects.last().live)

    def test_publishing_officer_cannot_access_the_add_page(self):
        self.client.force_login(self.publishing_officer)

        response = self.client.get(self.add_url, follow=True)
        self.assertContains(response, "Sorry, you do not have permission to access this area.")

    def test_publishing_officer_cannot_publish(self):
        self.client.force_login(self.publishing_officer)
        response = self.client.post(
            self.add_url,
            data={"name": "New definition", "definition": rich_text("definition"), "action-publish": "action-publish"},
            follow=True,
        )
        self.assertContains(response, "Sorry, you do not have permission to access this area.")


class PageBreadcrumbsTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.series = ArticleSeriesPageFactory()
        cls.statistical_article = StatisticalArticlePageFactory(parent=cls.series)

    def setUp(self):
        self.dummy_request = get_dummy_request()

    def test_breadcrumbs_output_format(self):
        """Test that get_breadcrumbs correctly outputs the parent pages in the correct format."""
        breadcrumbs_output = self.statistical_article.get_breadcrumbs(request=self.dummy_request)

        series_parent = self.series.get_parent()

        expected_entries = [
            {
                "url": series_parent.get_site().root_url,
                "text": "Home",
            },
            {
                "url": series_parent.get_parent().get_full_url(request=self.dummy_request),
                "text": series_parent.get_parent().title,
            },
            {
                "url": series_parent.get_full_url(request=self.dummy_request),
                "text": series_parent.title,
            },
        ]

        self.assertIsInstance(breadcrumbs_output, list)
        self.assertEqual(len(breadcrumbs_output), 3)
        self.assertListEqual(breadcrumbs_output, expected_entries)

    def test_breadcrumbs_include_self(self):
        """Test that get_breadcrumbs includes the page when request includes `is_for_subpage` attribute."""
        self.dummy_request.is_for_subpage = True
        breadcrumbs_output = self.statistical_article.get_breadcrumbs(request=self.dummy_request)

        series_parent = self.series.get_parent()

        expected_entries = [
            {
                "url": series_parent.get_site().root_url,
                "text": "Home",
            },
            {
                "url": series_parent.get_parent().get_full_url(request=self.dummy_request),
                "text": series_parent.get_parent().title,
            },
            {
                "url": series_parent.get_full_url(request=self.dummy_request),
                "text": series_parent.title,
            },
            {
                "url": self.statistical_article.get_full_url(request=self.dummy_request),
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
        self.dummy_request = get_dummy_request()

    def test_canonical_url(self):
        """Test that get_canonical_url returns the correct full URL for a page, including base URL."""
        canonical_url = self.information_page.get_canonical_url(self.dummy_request)

        self.assertEqual(canonical_url, self.information_page.get_full_url(self.dummy_request))


class AnalyticsValuesTestCase(TestCase):
    def test_parent_topic_or_theme(self):
        """Test the parent_topic_or_theme property returns the parent topic page for an InformationPage."""
        topic_page = TopicPageFactory()
        information_page = InformationPageFactory(parent=topic_page)

        self.assertEqual(information_page.parent_topic_or_theme, topic_page)

    def test_parent_topic_or_theme_none(self):
        """Test that the parent_topic_or_theme property returns None for a HomePage (which has no parent topic)."""
        home_page = HomePage.objects.first()
        self.assertIsNone(home_page.parent_topic_or_theme)

    def test_parent_topic_or_theme_for_topic_page(self):
        """Test that the parent_topic_or_theme property returns self TopicPage."""
        topic_page = TopicPageFactory()
        self.assertEqual(topic_page.parent_topic_or_theme, topic_page)

    def test_parent_topic_or_theme_for_theme_page(self):
        """Test that the parent_topic_or_theme property returns self ThemePage."""
        theme_page = ThemePageFactory()
        self.assertEqual(theme_page.parent_topic_or_theme, theme_page)

    def test_analytics_content_group(self):
        """Test that the analytics content group is the slug of the parent topic page."""
        topic_page = TopicPageFactory()
        information_page = InformationPageFactory(parent=topic_page)

        content_group = information_page.analytics_content_group

        self.assertEqual(content_group, topic_page.slug)

    def test_analytics_content_theme(self):
        """Test that the analytics content theme is the title of the top level topic associated with the parent topic
        page.
        """
        top_level_topic = Topic(id=1111, title="Test Analytics Theme", description="test")
        Topic.save_new(top_level_topic)
        topic = Topic(id=1112, title="Test Topic", description="test 2")
        Topic.save_new(topic, parent_topic=top_level_topic)
        topic_page = TopicPageFactory(topic=topic)
        information_page = InformationPageFactory(parent=topic_page)

        content_theme = information_page.analytics_content_theme
        self.assertEqual(content_theme, top_level_topic.title)

    def test_default_analytics_values(self):
        """Test that the analytics values are correctly set for a page."""
        information_page = InformationPageFactory()
        analytics_values = information_page.cached_analytics_values

        self.assertEqual(analytics_values.get("pageTitle"), information_page.title)
        self.assertEqual(analytics_values.get("contentType"), information_page.analytics_content_type)
        self.assertEqual(analytics_values.get("contentGroup"), information_page.analytics_content_group)
        self.assertEqual(analytics_values.get("contentTheme"), information_page.analytics_content_theme)
