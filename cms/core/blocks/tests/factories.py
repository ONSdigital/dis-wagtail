import factory

from cms.core.blocks.base import LinkBlock
from wagtail_factories import PageChooserBlockFactory, StructBlockFactory


class LinkBlockFactory(StructBlockFactory):
    """Factory for LinkBlock."""

    class Meta:
        model = LinkBlock

    title = factory.Faker("text", max_nb_chars=20)
    page = factory.Maybe(factory.SubFactory(PageChooserBlockFactory), None)
    external_url = factory.Faker("url")
