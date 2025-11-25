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

    def test_build_page_uri_strips_first_segment_various_home_slugs(self):
        test_vectors = [
            ("/home/section/page/", "/section/page/", "/section/page"),
            ("/inicio/article/", "/article/", "/article"),
            ("/accueil/reports/2025/q1/", "/reports/2025/q1/", "/reports/2025/q1"),
            ("/start/x/", "/x/", "/x"),
            ("/root/only-seg/", "/only-seg/", "/only-seg"),
        ]
        for url_path, expected_with_slash, expected_without_slash in test_vectors:
            for append_slash, expected in [(True, expected_with_slash), (False, expected_without_slash)]:
                with (
                    self.subTest(url_path=url_path, WAGTAIL_APPEND_SLASH=append_slash),
                    self.settings(WAGTAIL_APPEND_SLASH=append_slash),
                ):
                    dummy = type("DummyPage", (), {})()
                    dummy.url_path = url_path
                    result = build_page_uri(dummy)
                    self.assertEqual(result, expected)
