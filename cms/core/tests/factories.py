import factory
import wagtail_factories
from wagtail import blocks
from wagtail.rich_text import RichText
from wagtail_factories.blocks import BlockFactory

from cms.core.models import ContactDetails


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


# Section Block Factories


class SectionContentBlockFactory(wagtail_factories.StructBlockFactory):
    """Factory for Section content block."""

    title = factory.Faker("text", max_nb_chars=50)
    content = wagtail_factories.StreamFieldFactory(
        {
            "rich_text": factory.SubFactory(RichTextBlockFactory),
        }
    )


class SectionBlockFactory(wagtail_factories.StructBlockFactory):
    """Factory for Section StructBlock."""

    title = factory.Faker("text", max_nb_chars=50)
    content = factory.SubFactory(SectionContentBlockFactory)
