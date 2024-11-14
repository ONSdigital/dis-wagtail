from datetime import timedelta
from typing import ClassVar

import factory
import wagtail_factories
from django.utils import timezone

from cms.analysis.models import AnalysisPage, AnalysisSeries
from cms.core.tests.factories import ContactDetailsFactory, RichTextBlockFactory
from cms.topics.tests.factories import TopicPageFactory


class HeadlineFigureBlockFactory(wagtail_factories.StructBlockFactory):
    """Factory for HeadlineFigure block."""

    title = wagtail_factories.CharBlockFactory()
    figure = wagtail_factories.CharBlockFactory()
    trend = wagtail_factories.CharBlockFactory()


class SectionContentBlockFactory(wagtail_factories.StructBlockFactory):
    """Factory for Section content block."""

    title = factory.Faker("text", max_nb_chars=50)
    content = wagtail_factories.StreamFieldFactory(
        {
            "rich_text": factory.SubFactory(RichTextBlockFactory),
        }
    )


class SectionBlockFactory(wagtail_factories.StructBlockFactory):
    """Factory for Section block."""

    title = factory.Faker("text", max_nb_chars=50)
    content = factory.SubFactory(SectionContentBlockFactory)


class AnalysisSeriesFactory(wagtail_factories.PageFactory):
    """Factory for AnalysisSeries."""

    class Meta:
        model = AnalysisSeries

    title = factory.Faker("sentence", nb_words=4)
    parent = factory.SubFactory(TopicPageFactory)


class AnalysisPageFactory(wagtail_factories.PageFactory):
    """Factory for AnalysisPage."""

    class Meta:
        model = AnalysisPage
        django_get_or_create: ClassVar[list[str]] = ["slug", "parent"]

    title = factory.Faker("sentence", nb_words=4)
    parent = factory.SubFactory(AnalysisSeriesFactory)

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
