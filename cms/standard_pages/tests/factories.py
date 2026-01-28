import factory
import wagtail_factories

from cms.core.tests.factories import SectionBlockFactory
from cms.home.models import HomePage
from cms.standard_pages.models import IndexPage, InformationPage


class IndexPageFactory(wagtail_factories.PageFactory):
    """Factory for IndexPage."""

    class Meta:
        model = IndexPage

    parent = factory.LazyFunction(lambda: HomePage.objects.first())  # pylint: disable=unnecessary-lambda
    title = factory.Faker("sentence", nb_words=4)
    summary = factory.Faker("text", max_nb_chars=100)


class InformationPageFactory(wagtail_factories.PageFactory):
    """Factory for InformationPage."""

    class Meta:
        model = InformationPage

    parent = factory.SubFactory(IndexPageFactory)
    title = factory.Faker("sentence", nb_words=4)
    summary = factory.Faker("text", max_nb_chars=100)
    content = wagtail_factories.StreamFieldFactory({"section": factory.SubFactory(SectionBlockFactory)})
