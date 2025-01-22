import factory
import wagtail_factories

from cms.core.tests.factories import FeaturedItemBlockFactory, RelatedContentBlockFactory
from cms.standard_pages.models import IndexPage


class IndexPageFactory(wagtail_factories.PageFactory):
    """Factory for IndexPage."""

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
