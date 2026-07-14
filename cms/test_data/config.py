from typing import Annotated, Self

from faker import Faker
from pydantic import BaseModel, ConfigDict, Field, NonNegativeInt, PositiveInt, model_validator

FractionalFloat = Annotated[float, Field(ge=0, le=1)]


class BaseConfigModel(BaseModel):
    """A base model which ensures unknown fields raise an error."""

    model_config = ConfigDict(extra="forbid")


class RangeConfig(BaseConfigModel):
    min: PositiveInt = 1
    max: PositiveInt

    @model_validator(mode="after")
    def check_bounds(self) -> Self:
        if self.min == self.max:
            raise ValueError("Range is unnecessary")
        if self.min > self.max:
            raise ValueError("min must be less than max")
        return self


class NonNegativeRangeConfig(RangeConfig):
    min: NonNegativeInt = 1


class ModelCreationConfig(BaseConfigModel):
    count: PositiveInt | RangeConfig = 1


class PageCreationConfig(ModelCreationConfig):
    published_probability: FractionalFloat = 0.5
    revisions: PositiveInt | RangeConfig = 1


class TopicCreationConfig(PageCreationConfig):
    datasets: NonNegativeInt | NonNegativeRangeConfig = 1
    dataset_manual_links: NonNegativeInt = 0
    explore_more: NonNegativeInt | NonNegativeRangeConfig = 1


def _lowest(count: int | RangeConfig) -> int:
    return count.min if isinstance(count, RangeConfig) else count


def _highest(count: int | RangeConfig) -> int:
    return count.max if isinstance(count, RangeConfig) else count


class TestDataConfig(BaseConfigModel):
    datasets: ModelCreationConfig = ModelCreationConfig()
    images: ModelCreationConfig = ModelCreationConfig()
    topics: TopicCreationConfig = TopicCreationConfig(count=3)

    @model_validator(mode="after")
    def check_topic_datasets(self):
        # Import here to avoid module level model imports
        from cms.topics.models import MAX_ITEMS_PER_SECTION  # pylint: disable=import-outside-toplevel

        dataset_lookups = _highest(self.topics.datasets)
        if dataset_lookups > _lowest(self.datasets.count):
            raise ValueError("Topic datasets cannot exceed datasets.count, dataset cannot be linked twice")
        if (dataset_lookups + self.topics.dataset_manual_links) > MAX_ITEMS_PER_SECTION:
            raise ValueError(
                f"topics.datasets and topics.dataset_manual_links cannot total more than {MAX_ITEMS_PER_SECTION} items"
            )

        return self

    def get_count(self, data: int | RangeConfig, faker: Faker) -> int:
        if isinstance(data, int):
            return data

        return faker.random_int(min=data.min, max=data.max)
