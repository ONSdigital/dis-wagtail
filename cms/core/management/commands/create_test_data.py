from argparse import ArgumentParser
from typing import Any

import factory
import factory.fuzzy
import factory.random
from django.core.management.base import BaseCommand
from faker import Faker
from wagtail.models import Site

from cms.core.models import BasePage
from cms.taxonomy.models import Topic
from cms.taxonomy.tests.factories import SimpleTopicFactory
from cms.topics.tests.factories import TopicPageFactory

SEEDED_DATA_PREFIX = "Z-RANDOM "


class Command(BaseCommand):
    help = "Create random test data"

    def create_node_for_factory(
        self, factory_type: type[factory.base.BaseFactory], parent: BasePage, get_or_create_args=(), **kwargs
    ):
        instance = factory_type.build(**kwargs)

        matching = {s: getattr(instance, s) for s in get_or_create_args}

        if existing_instance := parent.get_children().filter(**matching).first():
            return existing_instance

        return parent.add_child(instance=instance)

    def add_arguments(self, parser: ArgumentParser):
        parser.add_argument(
            "--seed", nargs="?", default=4, type=int, help="Random seed to produce deterministic output"
        )
        parser.add_argument("--topics", nargs="?", default=3, type=int, help="Number of topics to create")

    def handle(self, *args: Any, **options: Any) -> None:
        # Seed randomness
        faker = Faker(locale="en_GB")
        faker.seed_instance(options["seed"])
        factory.random.reseed_random(options["seed"])

        root_page = Site.objects.first().root_page
        root_topic = Topic.objects.root_topic()

        title_factory = factory.LazyFunction(lambda: SEEDED_DATA_PREFIX + faker.sentence(nb_words=3))

        for _ in range(options["topics"]):
            topic = self.create_node_for_factory(
                SimpleTopicFactory, parent=root_topic, get_or_create_args=["id"], title=title_factory
            )

            topic_page = self.create_node_for_factory(
                TopicPageFactory, parent=root_page, get_or_create_args=["title"], title=title_factory, topic=topic
            )
