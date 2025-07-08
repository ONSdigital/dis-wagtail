import factory
import wagtail_factories

from cms.home.models import HomePage
from cms.taxonomy.tests.factories import TopicFactory
from cms.themes.models import ThemeIndexPage, ThemePage


class ThemeIndexPageFactory(wagtail_factories.PageFactory):
    class Meta:
        model = ThemeIndexPage

    parent = factory.LazyFunction(lambda: HomePage.objects.first())  # pylint: disable=unnecessary-lambda
    title = factory.Faker("sentence", nb_words=4)


class ThemePageFactory(wagtail_factories.PageFactory):
    """Factory for ThemePage."""

    class Meta:
        model = ThemePage

    parent = factory.SubFactory(ThemeIndexPageFactory)
    title = factory.Faker("sentence", nb_words=4)
    summary = factory.Faker("text", max_nb_chars=100)
    topic = factory.SubFactory(TopicFactory)
