from django.test import TestCase

from cms.articles.models import StatisticalArticlePage
from cms.articles.tests.factories import StatisticalArticlePageFactory
from cms.bundles.tests.factories import BundleFactory, BundlePageFactory
from cms.bundles.utils import get_bundleable_page_types, get_pages_in_active_bundles
from cms.methodology.models import MethodologyPage
from cms.release_calendar.models import ReleaseCalendarPage
from cms.standard_pages.models import IndexPage, InformationPage
from cms.topics.models import TopicPage


class BundlesUtilsTestCase(TestCase):
    def test_get_bundleable_page_types(self):
        page_types = get_bundleable_page_types()
        page_types.sort(key=lambda x: x.__name__)
        self.assertListEqual(
            page_types,
            [
                IndexPage,
                InformationPage,
                MethodologyPage,
                ReleaseCalendarPage,
                StatisticalArticlePage,
                TopicPage,
            ],
        )

    def test_get_pages_in_active_bundles(self):
        self.assertListEqual(get_pages_in_active_bundles(), [])

        bundle = BundleFactory()
        published_bundle = BundleFactory(published=True)

        page_in_active_bundle = StatisticalArticlePageFactory()
        page_in_published_bundle = StatisticalArticlePageFactory(parent=page_in_active_bundle.get_parent())
        _page_not_in_bundle = StatisticalArticlePageFactory(parent=page_in_active_bundle.get_parent())

        BundlePageFactory(parent=bundle, page=page_in_active_bundle)
        BundlePageFactory(parent=published_bundle, page=page_in_published_bundle)

        self.assertListEqual(get_pages_in_active_bundles(), [page_in_active_bundle.pk])
