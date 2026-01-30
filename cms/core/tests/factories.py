import factory
import wagtail_factories
from wagtail import blocks
from wagtail.rich_text import RichText
from wagtail_factories.blocks import (
    BlockFactory,
    PageChooserBlockFactory,
    StructBlockFactory,
)

from cms.core.blocks.related import LinkBlock, RelatedContentBlock
from cms.core.blocks.section_blocks import SectionBlock, SectionContentBlock
from cms.core.models import ContactDetails
from cms.core.models.snippets import Definition


class DateTimeBlockFactory(BlockFactory):
    """A factory for DateTimeBlock."""

    class Meta:
        model = blocks.DateTimeBlock


class DateBlockFactory(BlockFactory):
    """A factory for DateBlock."""

    class Meta:
        model = blocks.DateBlock


class URLBlockFactory(BlockFactory):
    """A factory for URLBlock."""

    class Meta:
        model = blocks.URLBlock


class RichTextBlockFactory(BlockFactory):
    """A factory for RichTextBlock."""

    class Meta:
        model = blocks.RichTextBlock

    @classmethod
    def _construct_block(cls, block_class, *args, **kwargs):
        if value := kwargs.get("value"):
            if not isinstance(value, RichText):
                value = RichText(value)
            return block_class().clean(value)
        return block_class().get_default()


class ContactDetailsFactory(factory.django.DjangoModelFactory):
    """Factory for ContactDetails."""

    class Meta:
        model = ContactDetails

    name = factory.Faker("name")
    email = factory.Faker("email")


class DefinitionFactory(factory.django.DjangoModelFactory):
    """Factory for Definition."""

    class Meta:
        model = Definition

    name = factory.Faker("text", max_nb_chars=20)
    definition = factory.Faker("text", max_nb_chars=100)


class SectionContentBlockFactory(StructBlockFactory):
    """Factory for Section content block."""

    class Meta:
        model = SectionContentBlock

    title = factory.Faker("text", max_nb_chars=50)
    content = wagtail_factories.StreamFieldFactory(
        {
            "rich_text": factory.SubFactory(RichTextBlockFactory),
        }
    )


class SectionBlockFactory(StructBlockFactory):
    """Factory for Section StructBlock."""

    class Meta:
        model = SectionBlock

    title = factory.Faker("text", max_nb_chars=50)
    content = factory.SubFactory(SectionContentBlockFactory)


class LinkBlockFactory(StructBlockFactory):
    """Factory for LinkBlock."""

    class Meta:
        model = LinkBlock

    title = factory.Faker("text", max_nb_chars=20)
    page = None
    external_url = factory.Faker("url")

    class Params:
        with_page = factory.Trait(page=factory.SubFactory(PageChooserBlockFactory), external_url=None)


class RelatedContentBlockFactory(LinkBlockFactory):
    class Meta:
        model = RelatedContentBlock

    description = factory.Faker("text", max_nb_chars=20)
