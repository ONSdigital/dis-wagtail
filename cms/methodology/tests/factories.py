from datetime import timedelta
from typing import ClassVar

import factory
import wagtail_factories
from django.utils import timezone

from cms.core.tests.factories import (
    ContactDetailsFactory,
    SectionContentBlockFactory,
)
from cms.methodology.models import MethodologyIndexPage, MethodologyPage, MethodologyRelatedPage
from cms.topics.tests.factories import TopicPageFactory


class MethodologyIndexPageFactory(wagtail_factories.PageFactory):
    class Meta:
        model = MethodologyIndexPage
        django_get_or_create: ClassVar[list[str]] = ["parent"]

    parent = factory.SubFactory(TopicPageFactory)


class MethodologyPageFactory(wagtail_factories.PageFactory):
    """Factory for MethodologyPage."""

    class Meta:
        model = MethodologyPage
        django_get_or_create: ClassVar[list[str]] = ["slug", "parent"]

    parent = factory.SubFactory(MethodologyIndexPageFactory)
    title = factory.Faker("sentence", nb_words=4)

    summary = factory.Faker("text", max_nb_chars=100)
    publication_date = factory.LazyFunction(lambda: timezone.now().date())
    last_revised_date = factory.LazyAttribute(lambda o: o.publication_date + timedelta(days=1))
    contact_details = factory.SubFactory(ContactDetailsFactory)

    content = wagtail_factories.StreamFieldFactory(
        {
            "section": factory.SubFactory(SectionContentBlockFactory),
        }
    )


class MethodologyRelatedPageFactory(factory.django.DjangoModelFactory):
    """Factory for MethodologyRelatedPage orderable model."""

    class Meta:
        model = MethodologyRelatedPage

    parent = factory.SubFactory(MethodologyPageFactory)
    page = factory.SubFactory("cms.articles.tests.factories.StatisticalArticlePageFactory")
    sort_order = factory.Sequence(lambda n: n)
