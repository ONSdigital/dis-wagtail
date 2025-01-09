from datetime import timedelta
from typing import ClassVar

import factory
import wagtail_factories
from django.utils import timezone

from cms.articles.models import ArticleSeriesPage, StatisticalArticlePage
from cms.core.tests.factories import ContactDetailsFactory, SectionBlockFactory
from cms.topics.tests.factories import TopicPageFactory


class HeadlineFigureBlockFactory(wagtail_factories.StructBlockFactory):
    """Factory for HeadlineFigure block."""

    title = wagtail_factories.CharBlockFactory()
    figure = wagtail_factories.CharBlockFactory()
    trend = wagtail_factories.CharBlockFactory()


class ArticleSeriesFactory(wagtail_factories.PageFactory):
    """Factory for ArticleSeriesPage."""

    class Meta:
        model = ArticleSeriesPage

    title = factory.Faker("sentence", nb_words=4)
    parent = factory.SubFactory(TopicPageFactory)


class StatisticalArticlePageFactory(wagtail_factories.PageFactory):
    """Factory for StatisticalArticlePage."""

    class Meta:
        model = StatisticalArticlePage
        django_get_or_create: ClassVar[list[str]] = ["slug", "parent"]

    title = factory.Faker("sentence", nb_words=4)
    parent = factory.SubFactory(ArticleSeriesFactory)

    summary = factory.Faker("text", max_nb_chars=100)
    news_headline = factory.Faker("text", max_nb_chars=50)
    main_points_summary = factory.Faker("text", max_nb_chars=200)
    release_date = factory.LazyFunction(lambda: timezone.now().date())
    next_release_date = factory.LazyAttribute(lambda o: o.release_date + timedelta(days=1))
    contact_details = factory.SubFactory(ContactDetailsFactory)

    headline_figures = wagtail_factories.StreamFieldFactory(
        {"headline_figure": factory.SubFactory(HeadlineFigureBlockFactory)}
    )
    content = wagtail_factories.StreamFieldFactory({"section": factory.SubFactory(SectionBlockFactory)})

    is_accredited = False
    is_census = False
    show_cite_this_page = True
