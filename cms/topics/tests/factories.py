import factory
import wagtail_factories

from cms.home.models import HomePage
from cms.taxonomy.tests.factories import TopicFactory
from cms.topics.models import TopicPage, TopicPageRelatedArticle, TopicPageRelatedMethodology


class TopicPageFactory(wagtail_factories.PageFactory):
    """Factory for TopicPage."""

    class Meta:
        model = TopicPage

    parent = factory.LazyFunction(lambda: HomePage.objects.first())  # pylint: disable=unnecessary-lambda
    title = factory.Faker("sentence", nb_words=4)
    summary = factory.Faker("text", max_nb_chars=100)
    topic = factory.SubFactory(TopicFactory)


class TopicPageRelatedArticleFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = TopicPageRelatedArticle

    parent = factory.SubFactory(TopicPageFactory)
    page = factory.SubFactory("cms.articles.tests.factories.StatisticalArticlePageFactory")
    sort_order = factory.Sequence(lambda n: n)


class TopicPageRelatedMethodologyFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = TopicPageRelatedMethodology

    parent = factory.SubFactory(TopicPageFactory)
    page = factory.SubFactory("cms.methodology.tests.factories.MethodologyPageFactory")
    sort_order = factory.Sequence(lambda n: n)
