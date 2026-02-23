from unittest.mock import call, patch

from django.test import TestCase, override_settings
from wagtail.blocks import StreamValue
from wagtail.coreutils import get_dummy_request
from wagtail.models import Locale

from cms.articles.models import ArticleSeriesPage, StatisticalArticlePage
from cms.articles.tests.factories import StatisticalArticlePageFactory
from cms.core.models import ContactDetails, Definition
from cms.datasets.blocks import DatasetStoryBlock
from cms.datasets.tests.factories import DatasetFactory
from cms.frontend_cache.signal_handlers import _get_indexed_page_models
from cms.home.models import HomePage
from cms.methodology.models import MethodologyPage
from cms.methodology.tests.factories import MethodologyPageFactory
from cms.release_calendar.models import ReleaseCalendarPage
from cms.standard_pages.models import CookiesPage, IndexPage, InformationPage
from cms.standard_pages.tests.factories import IndexPageFactory, InformationPageFactory
from cms.taxonomy.models import GenericPageToTaxonomyTopic
from cms.taxonomy.tests.factories import TopicFactory
from cms.themes.models import ThemeIndexPage, ThemePage
from cms.topics.models import TopicPage
from cms.topics.tests.factories import TopicPageFactory


@patch("cms.frontend_cache.cache.purge_urls_from_cache")
class PageFrontEndCacheInvalidationTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.home_page = HomePage.objects.first()

        cls.topic_1 = TopicFactory()
        cls.topic_2 = TopicFactory()

        cls.topic_page = TopicPageFactory(title="The topic page", topic=cls.topic_1)
        cls.topic_page.save_revision().publish()
        cls.topic_page_translation = cls.topic_page.get_translations().first()

        cls.another_topic_page = TopicPageFactory(title="Another topic page", live=False, topic=cls.topic_2)
        cls.another_topic_page_translation = cls.another_topic_page.get_translations().first()

        cls.statistical_article = StatisticalArticlePageFactory(
            parent__parent__parent=cls.topic_page, parent__title="Article series", title="The article"
        )
        cls.series_page = cls.statistical_article.get_parent().specific
        GenericPageToTaxonomyTopic.objects.create(page=cls.series_page, topic=cls.topic_2)

        cls.methodology_page = MethodologyPageFactory(parent__parent=cls.topic_page, title="Methodology")
        GenericPageToTaxonomyTopic.objects.create(page=cls.methodology_page, topic=cls.topic_2)

        cls.methodology_page_translation = cls.methodology_page.copy_for_translation(
            locale=Locale.objects.get(language_code="cy"), copy_parents=True, alias=True
        )

        cls.index_page = IndexPageFactory(title="Index page")
        cls.information_page = InformationPageFactory(parent=cls.index_page, title="Info page")

        cls.request = get_dummy_request()

        cls.series_url = cls.series_page.get_full_url(cls.request)
        cls.series_edition_url = f"{cls.series_url}/editions"
        cls.article_url = cls.statistical_article.get_full_url(cls.request)
        cls.article_related_data_url = f"{cls.article_url}/related-data"
        cls.topic_page_url = cls.topic_page.get_full_url(cls.request)
        cls.topic_page_translation_url = cls.topic_page_translation.get_full_url(cls.request)
        cls.another_topic_page_url = cls.another_topic_page.get_full_url(cls.request)
        cls.another_topic_page_translation_url = cls.another_topic_page_translation.get_full_url(cls.request)

        cls.methodology_page_url = cls.methodology_page.get_full_url(cls.request)
        cls.methodology_page_translation_url = cls.methodology_page_translation.get_full_url(cls.request)
        cls.index_page_url = cls.index_page.get_full_url(cls.request)
        cls.information_page_url = cls.information_page.get_full_url(cls.request)

    def test_excluded_page_types(self, _patched_purge_urls):
        self.assertEqual(
            _get_indexed_page_models(),
            {
                CookiesPage,
                IndexPage,
                InformationPage,
                ArticleSeriesPage,
                StatisticalArticlePage,
                MethodologyPage,
                ReleaseCalendarPage,
                TopicPage,
                ThemePage,
                ThemeIndexPage,
            },
        )

    @patch("cms.frontend_cache.cache.purge_page_from_frontend_cache")
    def test_excluded_page_types__dont_react(self, patched_purge_page, patched_purge_urls):
        self.home_page.save_revision().publish()

        patched_purge_page.assert_not_called()
        patched_purge_urls.assert_not_called()

    def _get_base_expected_statistical_page_urls_to_purge(self, with_translation=True):
        urls = {
            self.article_url,
            self.article_related_data_url,
            self.series_url,
            self.series_edition_url,
            f"{self.series_edition_url}?page=1",
            self.topic_page_url,
        }
        if with_translation:
            urls.add(self.topic_page_translation_url)

        return urls

    def test_page_publish__statistical_article(self, patched_purge_urls):
        self.statistical_article.save_revision().publish()

        patched_purge_urls.assert_called_once_with(self._get_base_expected_statistical_page_urls_to_purge())

    def test_page_publish__statistical_article__with_related_terms(self, patched_purge_urls):
        # now publish the second topic, then our page.
        self.another_topic_page.save_revision().publish()
        patched_purge_urls.reset_mock()

        self.statistical_article.save_revision().publish()

        expected_urls = self._get_base_expected_statistical_page_urls_to_purge() | {
            self.another_topic_page.get_full_url(self.request),
            self.another_topic_page_translation.get_full_url(self.request),
        }
        patched_purge_urls.assert_called_once_with(expected_urls)

    def test_page_publish__statistical_article__and_parent_topic_with_proper_translation(self, patched_purge_urls):
        self.topic_page_translation.alias_of = None
        self.topic_page_translation.save_revision().publish()

        self.statistical_article.save_revision().publish()

        patched_purge_urls.assert_called_with(
            self._get_base_expected_statistical_page_urls_to_purge(with_translation=False)
        )

    def test_page_publish__statistical_article_with_related_data(self, patched_purge_urls):
        dataset = DatasetFactory()
        self.statistical_article.datasets = StreamValue(
            DatasetStoryBlock(),
            stream_data=[("dataset_lookup", dataset)] * 6,
        )
        self.statistical_article.save_revision().publish()

        expected_urls = self._get_base_expected_statistical_page_urls_to_purge()
        expected_urls.add(f"{self.article_related_data_url}?page=1")
        patched_purge_urls.assert_called_once_with(expected_urls)

        with override_settings(RELATED_DATASETS_PER_PAGE=2):
            self.statistical_article.save_revision().publish()

            expected_urls |= {f"{self.article_related_data_url}?page=2", f"{self.article_related_data_url}?page=3"}
            patched_purge_urls.assert_called_with(expected_urls)

    @override_settings(PREVIOUS_RELEASES_PER_PAGE=1)
    def test_page_publish__article_series_with_multiple_editions(self, patched_purge_urls):
        StatisticalArticlePageFactory(parent=self.series_page, live=True)

        self.series_page.save_revision().publish()

        patched_purge_urls.assert_called_once_with(
            {
                self.series_url,
                self.series_edition_url,
                f"{self.series_edition_url}?page=1",
                f"{self.series_edition_url}?page=2",
            }
        )

    def test_page_publish__methodology(self, patched_purge_urls):
        self.methodology_page.save_revision().publish()

        self.assertEqual(patched_purge_urls.call_count, 2)
        patched_purge_urls.assert_has_calls(
            [
                # the published page
                call(
                    {
                        self.methodology_page_url,
                        self.topic_page_url,
                        self.topic_page_translation_url,
                    }
                ),
                # the follow-up alias page, as called by PublishPageRevisionAction
                # https://github.com/wagtail/wagtail/blob/faadee05ca/wagtail/actions/publish_page_revision.py#L61
                # https://github.com/wagtail/wagtail/blob/faadee05ca/wagtail/models/pages.py#L1176
                call({self.methodology_page_translation_url}),
            ]
        )

    def test_page_publish__methodology_with_related_terms(self, patched_purge_urls):
        # now publish the second topic, then our page.
        self.another_topic_page.save_revision().publish()
        patched_purge_urls.reset_mock()
        self.methodology_page.save_revision().publish()

        patched_purge_urls.assert_has_calls(
            [
                # the published page + linked
                call(
                    {
                        self.methodology_page_url,
                        self.topic_page_url,
                        self.topic_page_translation_url,
                        self.another_topic_page_url,
                        self.another_topic_page_translation_url,
                    }
                ),
                # the alias page
                call({self.methodology_page_translation_url}),
            ]
        )

    def test_page_publish__information_page(self, patched_purge_urls):
        self.information_page.save_revision().publish()
        patched_purge_urls.assert_called_once_with(
            {
                self.information_page_url,
                self.index_page_url,
            }
        )

    def test_page_publish__information_page__referenced_in_statistical_article(self, patched_purge_urls):
        with self.captureOnCommitCallbacks(execute=True):
            content = [
                {
                    "type": "related_links",
                    "value": [{"page": self.information_page.pk}],
                },
            ]
            self.statistical_article.content = [{"type": "section", "value": {"content": content, "title": "Section"}}]
            self.statistical_article.save()

            self.statistical_article.save_revision().publish()

        self.information_page.save_revision().publish()
        patched_purge_urls.assert_called_with(
            {
                self.information_page_url,
                self.index_page_url,
                self.article_url,
                self.article_related_data_url,
            }
        )

    def test_page_publish__no_special_case(self, patched_purge_urls):
        self.index_page.save_revision().publish()
        patched_purge_urls.assert_called_once_with({self.index_page_url})

    @patch("cms.frontend_cache.cache.purge_page_from_frontend_cache")
    def test_page_unpublish__calls_purge_page_like_page_publish(self, patched_purge_page, _patched_purge_urls):
        self.information_page.save_revision().publish()
        patched_purge_page.assert_called_once_with(self.information_page)
        patched_purge_page.reset_mock()

        self.information_page.unpublish()
        patched_purge_page.assert_called_once_with(self.information_page)

    def test_page_delete(self, patched_purge_urls):
        self.index_page.delete()

        patched_purge_urls.assert_called_with({self.index_page_url, self.information_page_url})


@patch("cms.frontend_cache.cache.purge_urls_from_cache")
class PageViaSnippetFrontEndCacheInvalidationTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.contact = ContactDetails.objects.create(name="PSF", email="psf@ons.gov.uk")
        cls.definition = Definition.objects.create(name="Term", definition="Definition")

        content = [
            {
                "type": "definitions",
                "value": [{"id": "d880c8a3-51ac-4dd7-b8d8-4cee0decf37d", "type": "item", "value": cls.definition.pk}],
            }
        ]

        cls.statistical_article = StatisticalArticlePageFactory(
            content=[{"type": "section", "value": {"content": content, "title": "Section"}}],
            contact_details=cls.contact,
        )

        # should not appear in purge calls
        cls.draft_statistical_article = StatisticalArticlePageFactory(
            content=[{"type": "section", "value": {"content": content, "title": "Section"}}],
            contact_details=cls.contact,
            live=False,
        )

        cls.statistical_article_url = cls.statistical_article.get_full_url(get_dummy_request())
        cls.statistical_article_related_data_url = f"{cls.statistical_article_url}/related-data"

    def setUp(self):
        # doing this here to avoid noise from deferred internal search index update via tasks
        with self.captureOnCommitCallbacks(execute=True):
            self.statistical_article.save()

    def test_publish__contact_details(self, mocked_purge_urls):
        self.contact.save_revision().publish()

        mocked_purge_urls.assert_called_once_with(
            {self.statistical_article_url, self.statistical_article_related_data_url}
        )

    def test_unpublish__contact_details(self, mocked_purge_urls):
        self.contact.unpublish()

        mocked_purge_urls.assert_called_once_with(
            {self.statistical_article_url, self.statistical_article_related_data_url}
        )

    def test_publish__definition(self, mocked_purge_urls):
        self.definition.save_revision().publish()

        mocked_purge_urls.assert_called_once_with(
            {self.statistical_article_url, self.statistical_article_related_data_url}
        )

    def test_unpublish__definition(self, mocked_purge_urls):
        self.definition.unpublish()

        mocked_purge_urls.assert_called_once_with(
            {self.statistical_article_url, self.statistical_article_related_data_url}
        )

    def test_delete(self, mocked_purge_urls):
        self.contact.delete()

        mocked_purge_urls.assert_called_once_with(
            {self.statistical_article_url, self.statistical_article_related_data_url}
        )
