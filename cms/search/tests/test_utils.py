from django.test import TestCase
from wagtail.models import Page

from cms.articles.models import ArticleSeriesPage, ArticlesIndexPage
from cms.articles.tests.factories import StatisticalArticlePageFactory
from cms.search.utils import build_page_uri, get_model_by_name


class SearchUtilsTests(TestCase):
    def test_get_model_by_name(self):
        model_names = {
            "Page": Page,
            "ArticlesIndexPage": ArticlesIndexPage,
            "ArticleSeriesPage": ArticleSeriesPage,
        }
        for name, model in model_names.items():
            with self.subTest(model_name=name):
                result = get_model_by_name(name)
                self.assertEqual(result, model)

    def test_build_page_uri_with_append_slash(self):
        for append_slash, expected in [
            (False, "/topic-page/articles/article-series/statistical-article"),
            (True, "/topic-page/articles/article-series/statistical-article/"),
        ]:
            with self.subTest(WAGTAIL_APPEND_SLASH=append_slash), self.settings(WAGTAIL_APPEND_SLASH=append_slash):
                page = StatisticalArticlePageFactory()
                page.url_path = "/home/topic-page/articles/article-series/statistical-article/"
                result = build_page_uri(page)
                self.assertEqual(result, expected)
