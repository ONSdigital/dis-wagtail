from argparse import ArgumentParser, ArgumentTypeError
from itertools import count
from pathlib import Path
from typing import Any

import factory
import factory.fuzzy
import factory.random
from django.core.management.base import BaseCommand
from faker import Faker
from pydantic import ValidationError
from treebeard.mp_tree import MP_Node
from wagtail.models import Site

from cms.datasets.tests.factories import DatasetFactory
from cms.taxonomy.models import Topic
from cms.taxonomy.tests.factories import SimpleTopicFactory
from cms.test_data.config import TestDataConfig
from cms.test_data.factories import ImageFactory
from cms.test_data.utils import SEEDED_DATA_PREFIX
from cms.topics.tests.factories import TopicPageFactory


def validate_config_file(val: str) -> TestDataConfig:
    config_path = Path(val)

    if not config_path.is_file() or config_path.suffix != ".json":
        raise ArgumentTypeError(f"{val} does not exist or is not a valid JSON file")
    try:
        return TestDataConfig.model_validate_json(config_path.read_text())
    except ValidationError as e:
        raise ArgumentTypeError(str(e)) from e


class Command(BaseCommand):
    help = "Create random test data"

    def create_node_for_factory(
        self,
        factory_type: type[factory.base.BaseFactory],
        parent: MP_Node,
        get_or_create_args: list[str] | None = None,
        **kwargs: Any,
    ) -> MP_Node:
        instance = factory_type.build(**kwargs)

        matching = {s: getattr(instance, s) for s in (get_or_create_args or [])}

        if existing_instance := parent.get_children().filter(**matching).first():
            return existing_instance

        created_node = parent.add_child(instance=instance)

        return created_node

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "--seed", nargs="?", default=4, type=int, help="Random seed to produce deterministic output"
        )
        parser.add_argument("--config", type=validate_config_file, help="Config file")
        parser.add_argument(
            "--noinput",
            "--no-input",
            action="store_false",
            dest="interactive",
            help="Tells Django to NOT prompt the user for input of any kind.",
        )

    def confirm_action(self, seed: int) -> bool:
        self.stdout.write("You are about to create test data in the database.", self.style.NOTICE)

        self.stdout.write(
            f"Enter the seed ({seed}) to continue: ",
            ending="",
        )
        result = input()
        try:
            int_result = int(result)
        except ValueError:
            self.stdout.write("Invalid input", self.style.ERROR)
            return False

        if int_result != seed:
            self.stdout.write("Incorrect input", self.style.ERROR)
            return False

        return True

    def handle(self, *args: Any, **options: Any) -> None:
        if options["interactive"] and not self.confirm_action(options["seed"]):
            return

        config: TestDataConfig = options["config"]

        # Seed randomness
        faker = Faker(locale="en_GB")
        faker.seed_instance(options["seed"])
        factory.Faker._DEFAULT_LOCALE = "en_GB"  # pylint: disable=protected-access
        factory.random.reseed_random(options["seed"])  # type: ignore[no-untyped-call]

        root_page = Site.objects.get(is_default_site=True).root_page
        root_topic = Topic.objects.root_topic()

        title_factory = factory.LazyFunction(lambda: SEEDED_DATA_PREFIX + faker.sentence(nb_words=3))  # type: ignore[no-untyped-call]

        images = ImageFactory.create_batch(config.images.get_count(faker), title=title_factory)

        datasets = DatasetFactory.create_batch(config.datasets.get_count(faker), title=title_factory)

        for _ in range(config.topics.get_count(faker)):
            topic = self.create_node_for_factory(
                SimpleTopicFactory, parent=root_topic, get_or_create_args=["id"], title=title_factory
            )

            topic_kwargs = {}

            topic_datasets_counter = count()
            for _ in range(config.topics.datasets_count(faker)):
                topic_kwargs[f"datasets__{next(topic_datasets_counter)}__dataset_lookup__dataset"] = (
                    faker.random_element(datasets)
                )

            for _ in range(config.topics.dataset_manual_links):
                topic_kwargs[f"datasets__{next(topic_datasets_counter)}"] = "manual_link"

            for i in range(config.topics.explore_more_count(faker)):
                if i % 2 == 0:
                    topic_kwargs[f"explore_more__{i}__internal_link__page"] = root_page
                    topic_kwargs[f"explore_more__{i}__internal_link__thumbnail__image"] = faker.random_element(images)
                else:
                    topic_kwargs[f"explore_more__{i}__external_link__thumbnail__image"] = faker.random_element(images)

            topic_page = self.create_node_for_factory(
                TopicPageFactory,
                parent=root_page,
                get_or_create_args=["title"],
                title=title_factory,
                topic=topic,
                **topic_kwargs,
            )

            topic_page.specific.save_revision().publish()
