import factory
import wagtail_factories

from cms.home.models import HomePage
from cms.taxonomy.tests.factories import TopicFactory
from cms.themes.models import ThemePage


class ThemePageFactory(wagtail_factories.PageFactory):
    """Factory for ThemePage."""

    class Meta:
        model = ThemePage

    title = factory.Faker("sentence", nb_words=4)
    summary = factory.Faker("text", max_nb_chars=100)
    parent = factory.LazyFunction(lambda: HomePage.objects.first())  # pylint: disable=unnecessary-lambda
    topic = factory.SubFactory(TopicFactory)
