from datetime import timedelta

import factory
import wagtail_factories
from django.utils import timezone

from cms.core.enums import RelatedMethodologyType
from cms.datasets.tests.factories import DatasetStoryBlockFactory
from cms.home.models import HomePage
from cms.taxonomy.tests.factories import TopicFactory
from cms.topics.blocks import ExploreMoreExternalLinkBlock, ExploreMoreInternalLinkBlock, ExploreMoreStoryBlock
from cms.topics.models import TopicPage, TopicPageRelatedArticle, TopicPageRelatedMethodology


class ExploreMoreExternalLinkBlockFactory(wagtail_factories.StructBlockFactory):
    url = factory.Faker("url")
    title = factory.Faker("sentence")
    description = factory.Faker("text", max_nb_chars=100)
    thumbnail = factory.SubFactory(wagtail_factories.ImageChooserBlockFactory)

    class Meta:
        model = ExploreMoreExternalLinkBlock


class ExploreMoreInternalLinkBlockFactory(wagtail_factories.StructBlockFactory):
    page = factory.SubFactory(wagtail_factories.PageChooserBlockFactory)
    title = factory.Faker("sentence")
    description = factory.Faker("text", max_nb_chars=100)
    thumbnail = factory.SubFactory(wagtail_factories.ImageChooserBlockFactory)

    class Meta:
        model = ExploreMoreInternalLinkBlock


class ExploreMoreStoryBlockFactory(wagtail_factories.StreamBlockFactory):
    external_link = factory.SubFactory(ExploreMoreExternalLinkBlockFactory)
    internal_link = factory.SubFactory(ExploreMoreInternalLinkBlockFactory)

    class Meta:
        model = ExploreMoreStoryBlock


class TopicPageFactory(wagtail_factories.PageFactory):
    """Factory for TopicPage."""

    class Meta:
        model = TopicPage
        django_get_or_create = ("title", "parent")

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
    datasets = wagtail_factories.StreamFieldFactory(DatasetStoryBlockFactory)
    explore_more = wagtail_factories.StreamFieldFactory(ExploreMoreStoryBlockFactory)


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
    external_url = ""
    title = ""
    content_type = RelatedMethodologyType.METHODOLOGY
    sort_order = factory.Sequence(lambda n: n)
