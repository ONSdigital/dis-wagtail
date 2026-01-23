import itertools
from argparse import ArgumentParser, ArgumentTypeError
from functools import partial
from pathlib import Path
from typing import Any

import factory
import factory.random
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Model
from factory.base import Factory
from faker import Faker
from pydantic import ValidationError
from wagtail.models import Site

from cms.datasets.models import Dataset
from cms.datasets.tests.factories import DatasetFactory
from cms.images.models import CustomImage
from cms.taxonomy.models import Topic
from cms.taxonomy.tests.factories import SimpleTopicFactory
from cms.test_data.config import TestDataConfig
from cms.test_data.constants import SEEDED_DATA_PREFIX
from cms.test_data.factories import ImageFactory
from cms.topics.models import TopicPage
from cms.topics.tests.factories import TopicPageFactory


class TestDataFactory:
    def __init__(self, config: TestDataConfig, seed: int) -> None:
        self.config = config

        # Seed randomness
        self.faker = Faker(locale="en_GB")
        self.faker.seed_instance(seed)

        # NB: These modify global state
        factory.Faker._DEFAULT_LOCALE = "en_GB"
        factory.random.reseed_random(seed)  # type: ignore[no-untyped-call]

        self.title_factory = factory.LazyFunction(lambda: SEEDED_DATA_PREFIX + self.faker.sentence(nb_words=3))  # type: ignore[no-untyped-call]

        self.root_page = Site.objects.get(is_default_site=True).root_page

        self.model_registry: dict[type[Model], list[Model]] = {}

        self.get_config_count = partial(self.config.get_count, faker=self.faker)

    def create_batch_from_factory(
        self, factory_class: type[Factory], instance_count: int, factory_kwargs: dict
    ) -> list[Model]:
        """Create model instances from a given factory."""
        created = factory_class.create_batch(instance_count, **factory_kwargs)
        if factory_class._meta.model not in self.model_registry:
            # Do a copy just in case anything external tries to mutate it
            self.model_registry[factory_class._meta.model] = created.copy()
        else:
            self.model_registry[factory_class._meta.model].extend(created)
        return created

    def create_from_factory(self, factory_class: type[Factory], factory_kwargs: dict) -> Model:
        """Create a model instance from a given factory."""
        return self.create_batch_from_factory(factory_class, 1, factory_kwargs)[0]

    def random_model(self, model: type[Model]) -> Model:
        """Select a random previously-generated model."""
        try:
            return self.faker.random_element(self.model_registry[model])
        except KeyError:
            raise RuntimeError(f"{model!r} has not been created yet") from None

    @transaction.atomic
    def run(self) -> None:
        self._create_images()
        self._create_datasets()
        self._create_topics()

    def _create_images(self) -> None:
        self.create_batch_from_factory(
            ImageFactory, self.get_config_count(self.config.images.count), {"title": self.title_factory}
        )

    def _create_datasets(self) -> None:
        self.create_batch_from_factory(
            DatasetFactory, self.get_config_count(self.config.datasets.count), {"title": self.title_factory}
        )

    def _create_topics(self) -> None:
        root_topic = Topic.objects.root_topic()

        for _ in range(self.get_config_count(self.config.topics.count)):
            topic_kwargs = {
                # NB: Must be created using a separate factory, as TopicFactory isn't idempotent
                "topic": self.create_from_factory(
                    SimpleTopicFactory, {"parent": root_topic, "title": self.title_factory}
                ),
                "parent": self.root_page,
                "title": self.title_factory,
            }

            topic_datasets_counter = itertools.count()
            for _ in range(self.get_config_count(self.config.topics.datasets)):
                topic_kwargs[f"datasets__{next(topic_datasets_counter)}__dataset_lookup__dataset"] = self.random_model(
                    Dataset
                )

            for _ in range(self.config.topics.dataset_manual_links):
                topic_kwargs[f"datasets__{next(topic_datasets_counter)}"] = "manual_link"

            for i in range(self.get_config_count(self.config.topics.explore_more)):
                if i % 2 == 0:
                    topic_kwargs[f"explore_more__{i}__internal_link__page"] = self.root_page
                    topic_kwargs[f"explore_more__{i}__internal_link__thumbnail__image"] = self.random_model(CustomImage)
                else:
                    topic_kwargs[f"explore_more__{i}__external_link__thumbnail__image"] = self.random_model(CustomImage)

            topic_page: TopicPage = self.create_from_factory(TopicPageFactory, topic_kwargs)  # type: ignore[assignment]

            for _ in range(self.get_config_count(self.config.topics.revisions)):
                topic_page.specific.save_revision()

            if (
                not topic_page.live
                and topic_page.latest_revision_id
                and self.faker.boolean(int(self.config.topics.published_probability * 100))
            ):
                topic_page.specific.latest_revision.publish()


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

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "--seed", nargs="?", default=4, type=int, help="Random seed to produce deterministic output"
        )
        parser.add_argument("--config", type=validate_config_file, default=TestDataConfig(), help="Config file")
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

        TestDataFactory(options["config"], options["seed"]).run()
