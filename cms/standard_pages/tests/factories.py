import factory
import wagtail_factories
from django.utils import timezone

from cms.core.tests.factories import (
    RelatedContentBlockFactory,
    SectionBlockFactory,
)
from cms.home.models import HomePage
from cms.standard_pages.models import IndexPage, InformationPage


class IndexPageFactory(wagtail_factories.PageFactory):
    """Factory for IndexPage."""

    parent = factory.LazyFunction(lambda: HomePage.objects.first())  # pylint: disable=unnecessary-lambda

    class Meta:
        model = IndexPage

    description = factory.Faker("text", max_nb_chars=100)

    featured_pages = wagtail_factories.StreamFieldFactory(
        {"featured_page": factory.SubFactory(RelatedContentBlockFactory)}
    )

    content = factory.Faker("text", max_nb_chars=100)

    related_links = wagtail_factories.StreamFieldFactory(
        {"related_link": factory.SubFactory(RelatedContentBlockFactory)}
    )


class InformationPageFactory(wagtail_factories.PageFactory):
    """Factory for InformationPage."""

    parent = factory.SubFactory(IndexPageFactory)

    class Meta:
        model = InformationPage

    summary = factory.Faker("text", max_nb_chars=100)
    last_updated = factory.LazyFunction(lambda: timezone.now().date())
    content = wagtail_factories.StreamFieldFactory({"section": factory.SubFactory(SectionBlockFactory)})
