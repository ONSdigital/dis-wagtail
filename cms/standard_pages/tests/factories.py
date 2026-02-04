from datetime import timedelta

import factory
import wagtail_factories
from django.utils import timezone
from faker import Faker
from wagtail.blocks import StreamValue

from cms.home.models import HomePage
from cms.standard_pages.blocks.stream_blocks import CoreStoryBlock
from cms.standard_pages.models import IndexPage, InformationPage

fake = Faker()


class IndexPageFactory(wagtail_factories.PageFactory):
    """Factory for IndexPage."""

    class Meta:
        model = IndexPage

    parent = factory.LazyFunction(lambda: HomePage.objects.first())  # pylint: disable=unnecessary-lambda
    last_published_at = timezone.now() - timedelta(days=1)
    title = factory.Faker("sentence", nb_words=4)
    summary = factory.Faker("text", max_nb_chars=100)


class InformationPageFactory(wagtail_factories.PageFactory):
    class Meta:
        model = InformationPage

    parent = factory.SubFactory(IndexPageFactory)
    last_published_at = timezone.now() - timedelta(days=1)
    title = factory.Faker("sentence", nb_words=4)
    summary = "<p>Test summary</p>"

    # StreamFieldFactory doesn't reliably handle nested StructBlocks/StreamBlocks,
    # so we build the StreamValue manually with the exact structure Wagtail expects.
    @factory.lazy_attribute
    def content(self):
        return StreamValue(
            CoreStoryBlock(),
            [
                {
                    "type": "section",
                    "value": {
                        "title": fake.sentence(),
                        "content": [{"type": "rich_text", "value": f"<p>{fake.paragraph()}</p>"}],
                    },
                }
            ],
            is_lazy=True,
        )
