import factory
import wagtail_factories
from django.utils import timezone

from cms.core.tests.factories import (
    FeaturedItemBlockFactory,
    RelatedContentBlockFactory,
    SectionBlockFactory,
)
from cms.home.models import HomePage
from cms.standard_pages.models import IndexPage, InformationPage


class IndexPageFactory(wagtail_factories.PageFactory):
    """Factory for IndexPage."""

    parent = factory.LazyFunction(lambda: HomePage.objects.first())

    class Meta:
        model = IndexPage

    description = factory.Faker("text", max_nb_chars=100)

    featured_items = wagtail_factories.StreamFieldFactory(
        {"featured_item": factory.SubFactory(FeaturedItemBlockFactory)}
    )

    content = factory.Faker("text", max_nb_chars=100)

    related_links = wagtail_factories.StreamFieldFactory(
        {"related_link": factory.SubFactory(RelatedContentBlockFactory)}
    )


class InformationPageFactory(wagtail_factories.PageFactory):
    # parent = factory.SubFactory(IndexPageFactory)

    parent = factory.LazyFunction(lambda: IndexPage.objects.first())

    class Meta:
        model = InformationPage

    summary = factory.Faker("text", max_nb_chars=100)
    last_updated = factory.LazyFunction(lambda: timezone.now().date())
    content = wagtail_factories.StreamFieldFactory({"section": factory.SubFactory(SectionBlockFactory)})
