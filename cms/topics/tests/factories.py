import factory
import wagtail_factories

from cms.taxonomy.tests.factories import TopicFactory
from cms.themes.tests.factories import ThemePageFactory
from cms.topics.models import TopicPage


class TopicPageFactory(wagtail_factories.PageFactory):
    """Factory for TopicPage."""

    class Meta:
        model = TopicPage

    title = factory.Faker("sentence", nb_words=4)
    summary = factory.Faker("text", max_nb_chars=100)
    parent = factory.SubFactory(ThemePageFactory)
    topic = factory.SubFactory(TopicFactory)
