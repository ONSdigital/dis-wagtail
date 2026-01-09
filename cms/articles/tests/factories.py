from datetime import timedelta
from typing import ClassVar

import factory
import wagtail_factories
from django.utils import timezone

from cms.articles.models import ArticleSeriesPage, ArticlesIndexPage, StatisticalArticlePage
from cms.core.tests.factories import ContactDetailsFactory, SectionContentBlockFactory
from cms.topics.tests.factories import TopicPageFactory


class HeadlineFigureBlockFactory(wagtail_factories.StructBlockFactory):
    """Factory for HeadlineFigure block."""

    title = wagtail_factories.CharBlockFactory()
    figure = wagtail_factories.CharBlockFactory()
    trend = wagtail_factories.CharBlockFactory()


class ArticlesIndexPageFactory(wagtail_factories.PageFactory):
    class Meta:
        model = ArticlesIndexPage
        django_get_or_create: ClassVar[list[str]] = ["parent"]

    parent = factory.SubFactory(TopicPageFactory)
    title = factory.Faker("sentence", nb_words=4)


class ArticleSeriesPageFactory(wagtail_factories.PageFactory):
    """Factory for ArticleSeriesPage."""

    class Meta:
        model = ArticleSeriesPage

    parent = factory.SubFactory(ArticlesIndexPageFactory)
    title = factory.Faker("sentence", nb_words=4)


class StatisticalArticlePageFactory(wagtail_factories.PageFactory):
    """Factory for StatisticalArticlePage."""

    class Meta:
        model = StatisticalArticlePage
        django_get_or_create: ClassVar[list[str]] = ["slug", "parent"]

    parent = factory.SubFactory(ArticleSeriesPageFactory)
    title = factory.Faker("sentence", nb_words=4)

    summary = factory.Faker("text", max_nb_chars=100)
    news_headline = factory.Faker("text", max_nb_chars=50)
    main_points_summary = factory.Faker("text", max_nb_chars=200)
    release_date = factory.LazyFunction(lambda: timezone.now().date())
    next_release_date = factory.LazyAttribute(lambda o: o.release_date + timedelta(days=1))
    contact_details = factory.SubFactory(ContactDetailsFactory)
    listing_image = factory.SubFactory(wagtail_factories.ImageFactory)

    headline_figures = wagtail_factories.StreamFieldFactory({"figures": factory.SubFactory(HeadlineFigureBlockFactory)})
    content = wagtail_factories.StreamFieldFactory(
        {
            "section": factory.SubFactory(SectionContentBlockFactory),
        }
    )
    is_accredited = False
    is_census = False
    show_cite_this_page = True
    first_published_at = factory.LazyFunction(timezone.now)
    last_published_at = factory.LazyFunction(timezone.now)
