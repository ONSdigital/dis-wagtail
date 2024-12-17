from datetime import timedelta
from typing import ClassVar

import factory
import wagtail_factories
from django.utils import timezone

from cms.core.tests.factories import ContactDetailsFactory, SectionBlockFactory
from cms.methodology.models import MethodologyPage
from cms.topics.tests.factories import TopicPageFactory


class MethodologyPageFactory(wagtail_factories.PageFactory):
    """Factory for MethodologyPage."""

    parent = factory.SubFactory(TopicPageFactory)

    class Meta:
        model = MethodologyPage
        django_get_or_create: ClassVar[list[str]] = ["slug", "parent"]

    title = factory.Faker("sentence", nb_words=4)

    summary = factory.Faker("text", max_nb_chars=100)
    publication_date = factory.LazyFunction(lambda: timezone.now().date())
    last_revised_date = factory.LazyAttribute(lambda o: o.publication_date + timedelta(days=1))
    contact_details = factory.SubFactory(ContactDetailsFactory)

    content = wagtail_factories.StreamFieldFactory({"section": factory.SubFactory(SectionBlockFactory)})
