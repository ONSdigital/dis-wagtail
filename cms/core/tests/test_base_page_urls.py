from django.test import TestCase
from wagtail.test.utils import WagtailTestUtils

from cms.articles.tests.factories import ArticleSeriesPageFactory, StatisticalArticlePageFactory
from cms.home.models import HomePage


class TestBasePageURLs(WagtailTestUtils, TestCase):
    """Test that BasePage URL generation returns non-trailing slash URLs."""

    def setUp(self):
        self.root_page = HomePage.objects.first()
        # Create test pages
        self.series_page = ArticleSeriesPageFactory()
        self.article_page = StatisticalArticlePageFactory()

    def test_get_url_removes_trailing_slash(self):
        """Test that get_url returns URLs without trailing slashes."""
        # Test series page
        series_url = self.series_page.get_url()
        self.assertIsNotNone(series_url)
        self.assertFalse(series_url.endswith("/"), f"Series URL should not end with slash: {series_url}")

        # Test article page
        article_url = self.article_page.get_url()
        self.assertIsNotNone(article_url)
        self.assertFalse(article_url.endswith("/"), f"Article URL should not end with slash: {article_url}")
