from datetime import timedelta

import factory
import wagtail_factories
from django.utils import timezone

from cms.home.models import HomePage
from cms.taxonomy.tests.factories import TopicFactory
from cms.topics.models import TopicPage, TopicPageRelatedArticle, TopicPageRelatedMethodology


class TopicPageFactory(wagtail_factories.PageFactory):
    """Factory for TopicPage."""

    class Meta:
        model = TopicPage

    parent = factory.LazyFunction(lambda: HomePage.objects.first())  # pylint: disable=unnecessary-lambda
    first_published_at = factory.LazyAttribute(
        lambda o: timezone.now() - timedelta(days=10) if getattr(o, "live", True) else None
    )
    last_published_at = factory.LazyAttribute(
        lambda o: timezone.now() - timedelta(days=1) if getattr(o, "live", True) else None
    )
    title = factory.Faker("sentence", nb_words=4)
    summary = factory.Faker("text", max_nb_chars=100)
    topic = factory.SubFactory(TopicFactory)


class TopicPageRelatedArticleFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = TopicPageRelatedArticle

    parent = factory.SubFactory(TopicPageFactory)
    page = factory.SubFactory("cms.articles.tests.factories.StatisticalArticlePageFactory")
    external_url = ""
    title = ""
    sort_order = factory.Sequence(lambda n: n)


class TopicPageRelatedMethodologyFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = TopicPageRelatedMethodology

    parent = factory.SubFactory(TopicPageFactory)
    page = factory.SubFactory("cms.methodology.tests.factories.MethodologyPageFactory")
    sort_order = factory.Sequence(lambda n: n)
