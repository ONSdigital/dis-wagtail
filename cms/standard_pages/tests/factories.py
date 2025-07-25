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

    class Meta:
        model = IndexPage

    parent = factory.LazyFunction(lambda: HomePage.objects.first())  # pylint: disable=unnecessary-lambda
    title = factory.Faker("sentence", nb_words=4)
    summary = factory.Faker("text", max_nb_chars=100)

    featured_items = wagtail_factories.StreamFieldFactory(
        {"featured_item": factory.SubFactory(RelatedContentBlockFactory)}
    )

    content = factory.Faker("text", max_nb_chars=100)

    related_links = wagtail_factories.StreamFieldFactory(
        {"related_link": factory.SubFactory(RelatedContentBlockFactory)}
    )


class InformationPageFactory(wagtail_factories.PageFactory):
    """Factory for InformationPage."""

    class Meta:
        model = InformationPage

    parent = factory.SubFactory(IndexPageFactory)
    title = factory.Faker("sentence", nb_words=4)
    summary = factory.Faker("text", max_nb_chars=100)
    last_updated = factory.LazyFunction(lambda: timezone.now().date())
    content = wagtail_factories.StreamFieldFactory({"section": factory.SubFactory(SectionBlockFactory)})
