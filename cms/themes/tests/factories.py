import factory
import wagtail_factories

from cms.taxonomy.tests.factories import TopicFactory
from cms.themes.models import ThemeIndexPage, ThemePage


class ThemeIndexPageFactory(wagtail_factories.PageFactory):
    class Meta:
        model = ThemeIndexPage


class ThemePageFactory(wagtail_factories.PageFactory):
    """Factory for ThemePage."""

    class Meta:
        model = ThemePage

    title = factory.Faker("sentence", nb_words=4)
    summary = factory.Faker("text", max_nb_chars=100)
    parent = factory.SubFactory(ThemeIndexPageFactory)
    topic = factory.SubFactory(TopicFactory)
